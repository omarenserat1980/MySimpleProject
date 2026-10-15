"""Unified GitHub Control Plane for Electronic Brain."""
from __future__ import annotations
import hashlib, json, os, time, shutil, subprocess
from dataclasses import dataclass
from typing import Any
import httpx

class GitHubControlError(RuntimeError): pass

@dataclass(frozen=True)
class GitHubPolicy:
    read_only: frozenset[str] = frozenset({"repo.read","code.read","issues.read","pulls.read","actions.read","releases.read","security.read","projects.read","packages.read","search.read","users.read"})
    write_requires_approval: frozenset[str] = frozenset({"repo.write","code.write","issues.write","pulls.write","actions.write","releases.write","projects.write","packages.write","security.write"})
    blocked: frozenset[str] = frozenset({"billing.write","financial.transfer","secret.exfiltration"})

class GitHubControlPlane:
    """Single policy boundary for GitHub REST operations."""
    API = "https://api.github.com"
    VERSION = "2022-11-28"
    def __init__(self, token: str | None = None, policy: GitHubPolicy | None = None):
        self.token = token or os.getenv("BRAIN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or self._gh_token()
        
        self.policy = policy or GitHubPolicy(); self.audit: list[dict[str, Any]] = []
    @staticmethod
    def _gh_token() -> str | None:
        gh = shutil.which("gh") or shutil.which("gh.exe") or (r"C:\Program Files\GitHub CLI\gh.exe" if os.path.exists(r"C:\Program Files\GitHub CLI\gh.exe") else None)
        if not gh:
            return None
        try:
            out = subprocess.run([gh, "auth", "token", "--hostname", "github.com"], capture_output=True, text=True, timeout=10, check=True)
            value = out.stdout.strip()
            return value or None
        except (OSError, subprocess.SubprocessError):
            return None

    def configured(self) -> bool: return bool(self.token)
    def _auth(self):
        if not self.token: raise GitHubControlError("GITHUB_TOKEN_NOT_CONFIGURED")
        return {"Accept":"application/vnd.github+json","Authorization":f"Bearer {self.token}","X-GitHub-Api-Version":self.VERSION,"User-Agent":"Electronic-Brain-GitHub-Control-Plane"}
    def _record(self, action, capability, status, details):
        raw=json.dumps({"ts":time.time(),"action":action,"capability":capability,"status":status,"details":details},sort_keys=True)
        self.audit.append({"ts":time.time(),"action":action,"capability":capability,"status":status,"digest":hashlib.sha256(raw.encode()).hexdigest()})
    def authorize(self, capability, approved=False):
        if capability in self.policy.blocked:
            raise GitHubControlError(f"BLOCKED_CAPABILITY:{capability}")
        known = self.policy.read_only | self.policy.write_requires_approval
        if capability not in known:
            raise GitHubControlError(f"UNKNOWN_CAPABILITY:{capability}")
        if capability in self.policy.write_requires_approval and not approved:
            raise GitHubControlError(f"EXPLICIT_APPROVAL_REQUIRED:{capability}")
    def request(self, method, path, *, capability="repo.read", approved=False, params=None, body=None, timeout=30.0):
        method = method.upper()
        if method not in {"GET", "HEAD", "OPTIONS"} and capability not in self.policy.write_requires_approval:
            raise GitHubControlError(f"MUTATION_REQUIRES_WRITE_CAPABILITY:{capability}")
        self.authorize(capability, approved)
        if not path.startswith("/"): path="/"+path
        try:
            with httpx.Client(timeout=timeout) as client: r=client.request(method.upper(),self.API+path,headers=self._auth(),params=params,json=body)
            status="SUCCESS" if r.status_code<400 else "FAILED"; self._record(method.upper()+" "+path,capability,status,{"http_status":r.status_code,"params":params or {}})
            if r.status_code>=400: raise GitHubControlError(f"GITHUB_HTTP_{r.status_code}:{r.text[:1000]}")
            return r.json() if r.content else {"ok":True,"status_code":r.status_code}
        except httpx.HTTPError as exc:
            self._record(method.upper()+" "+path,capability,"NETWORK_ERROR",{}); raise GitHubControlError(f"GITHUB_NETWORK_ERROR:{exc}") from exc
    def repository(self, owner, repo): return self.request("GET",f"/repos/{owner}/{repo}",capability="repo.read")
    def contents(self, owner, repo, path="", ref=None): return self.request("GET",f"/repos/{owner}/{repo}/contents/{path}",capability="code.read",params={"ref":ref} if ref else None)
    def write_contents(self, owner, repo, path, body, approved=False): return self.request("PUT",f"/repos/{owner}/{repo}/contents/{path}",capability="code.write",approved=approved,body=body)
    def issues(self, owner, repo, number=None): return self.request("GET",f"/repos/{owner}/{repo}/issues"+(f"/{number}" if number is not None else ""),capability="issues.read")
    def pull_request(self, owner, repo, number): return self.request("GET",f"/repos/{owner}/{repo}/pulls/{number}",capability="pulls.read")
    def actions_runs(self, owner, repo, page=1, per_page=100):
        """Fetch one page of workflow runs; GitHub permits at most 100 per page."""
        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")
        return self.request("GET", f"/repos/{owner}/{repo}/actions/runs",
                            capability="actions.read",
                            params={"page": page, "per_page": per_page})

    def actions_workflows_all(self, owner, repo, per_page=100, max_pages=1000):
        """Enumerate every workflow definition, failing closed if pagination is incomplete."""
        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")
        items = []
        for page in range(1, max_pages + 1):
            payload = self.request("GET", f"/repos/{owner}/{repo}/actions/workflows",
                                   capability="actions.read",
                                   params={"page": page, "per_page": per_page})
            batch = payload.get("workflows") if isinstance(payload, dict) else None
            if not isinstance(batch, list):
                raise GitHubControlError("ACTIONS_WORKFLOWS_INVALID_RESPONSE")
            items.extend(batch)
            if len(batch) < per_page:
                return {"workflows": items, "pages_fetched": page,
                        "complete": True, "count": len(items)}
        raise GitHubControlError("ACTIONS_WORKFLOWS_PAGINATION_LIMIT_REACHED")

    def actions_runs_last_24h(self, owner, repo, *, workflow_ids=None, now=None, per_page=100, max_pages=10):
        """Fetch the last 24h of runs per workflow to avoid the repository-wide 1,000-result cap.

        GitHub caps the repository-wide workflow-runs listing at 1,000 results.
        Splitting by workflow keeps each inventory independently paginatable; if
        any single workflow still exceeds the API cap, fail closed rather than
        claiming a complete audit.
        """
        from datetime import datetime, timedelta, timezone
        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")
        if workflow_ids is None:
            raise GitHubControlError("ACTIONS_WORKFLOW_IDS_REQUIRED")
        if any(not isinstance(workflow_id, int) or workflow_id <= 0 for workflow_id in workflow_ids):
            raise GitHubControlError("ACTIONS_WORKFLOW_ID_INVALID")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        current = current.astimezone(timezone.utc)
        cutoff = current - timedelta(hours=24)
        created = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        all_items = []
        total_count = 0
        pages_fetched = 0

        for workflow_id in workflow_ids:
            items = []
            expected_total = None
            for page in range(1, max_pages + 1):
                payload = self.request(
                    "GET", f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs",
                    capability="actions.read",
                    params={"page": page, "per_page": per_page, "created": ">=" + created},
                )
                if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
                    raise GitHubControlError("ACTIONS_RUNS_INVALID_RESPONSE")
                if expected_total is None:
                    expected_total = payload.get("total_count")
                    if not isinstance(expected_total, int) or expected_total < 0:
                        raise GitHubControlError("ACTIONS_RUNS_TOTAL_COUNT_MISSING")
                    if expected_total > 1000:
                        raise GitHubControlError("ACTIONS_RUNS_API_RESULT_CAP_EXCEEDED")
                batch = payload["workflow_runs"]
                items.extend(batch)
                pages_fetched += 1
                if len(items) >= expected_total:
                    break
                if len(batch) < per_page:
                    raise GitHubControlError("ACTIONS_RUNS_PAGINATION_INCOMPLETE")
            else:
                raise GitHubControlError("ACTIONS_RUNS_PAGINATION_LIMIT_REACHED")
            if expected_total is not None and len(items) != expected_total:
                raise GitHubControlError("ACTIONS_RUNS_PAGINATION_INCOMPLETE")
            total_count += len(items)
            all_items.extend(items)

        filtered = []
        for run in all_items:
            if not isinstance(run, dict):
                raise GitHubControlError("WORKFLOW_RUN_RECORD_INVALID")
            stamp = run.get("created_at")
            if not isinstance(stamp, str):
                raise GitHubControlError("ACTIONS_RUN_TIMESTAMP_MISSING")
            try:
                created_at = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError as exc:
                raise GitHubControlError("ACTIONS_RUN_TIMESTAMP_INVALID") from exc
            if created_at.tzinfo is None:
                raise GitHubControlError("ACTIONS_RUN_TIMESTAMP_TIMEZONE_MISSING")
            if cutoff <= created_at.astimezone(timezone.utc) <= current:
                filtered.append(run)

        return {"workflow_runs": filtered, "pages_fetched": pages_fetched,
                "count": len(filtered), "api_total_count": total_count,
                "window_start": cutoff.isoformat(), "window_end": current.isoformat(),
                "complete": True}
    def dispatch_workflow(self, owner, repo, workflow_id, ref="main", inputs=None, approved=False):
        """Dispatch a workflow through GitHub REST; mutable action requires explicit approval."""
        body={"ref":ref}
        if inputs:
            body["inputs"]=inputs
        return self.request("POST",f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",capability="actions.write",approved=approved,body=body)
    def releases(self, owner, repo): return self.request("GET",f"/repos/{owner}/{repo}/releases",capability="releases.read")
    def search(self, query, search_type="repositories"): return self.request("GET",f"/search/{search_type}",capability="search.read",params={"q":query})
    def rest(self, method, path, capability="repo.read", approved=False, params=None, body=None):
        """Governed escape hatch for the GitHub REST API; all mutations remain approval-gated."""
        return self.request(method, path, capability=capability, approved=approved, params=params, body=body)

    def capability_catalog(self):
        return {"ok":True,"gateway":"GitHubControlPlane","configured":self.configured(),"domains":["repositories","git-data","contents","branches","tags","commits","issues","pull-requests","reviews","actions","releases","packages","projects","security","search","users","organizations","webhooks"],"execution_model":["discover","authorize","execute","verify","audit"],"write_policy":"explicit approval for mutable operations"}

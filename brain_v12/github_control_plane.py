"""Unified GitHub Control Plane for Electronic Brain."""
from __future__ import annotations
import hashlib, json, os, time
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
        self.token = token or os.getenv("BRAIN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        self.policy = policy or GitHubPolicy(); self.audit: list[dict[str, Any]] = []
    def configured(self) -> bool: return bool(self.token)
    def _auth(self):
        if not self.token: raise GitHubControlError("GITHUB_TOKEN_NOT_CONFIGURED")
        return {"Accept":"application/vnd.github+json","Authorization":f"Bearer {self.token}","X-GitHub-Api-Version":self.VERSION,"User-Agent":"Electronic-Brain-GitHub-Control-Plane"}
    def _record(self, action, capability, status, details):
        raw=json.dumps({"ts":time.time(),"action":action,"capability":capability,"status":status,"details":details},sort_keys=True)
        self.audit.append({"ts":time.time(),"action":action,"capability":capability,"status":status,"digest":hashlib.sha256(raw.encode()).hexdigest()})
    def authorize(self, capability, approved=False):
        if capability in self.policy.blocked: raise GitHubControlError(f"BLOCKED_CAPABILITY:{capability}")
        if capability in self.policy.write_requires_approval and not approved: raise GitHubControlError(f"EXPLICIT_APPROVAL_REQUIRED:{capability}")
    def request(self, method, path, *, capability="repo.read", approved=False, params=None, body=None, timeout=30.0):
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
    def actions_runs(self, owner, repo, page=1, per_page=30): return self.request("GET",f"/repos/{owner}/{repo}/actions/runs",capability="actions.read",params={"page":page,"per_page":per_page})
    def dispatch_workflow(self, owner, repo, workflow_id, ref="main", inputs=None, approved=False):
        """Dispatch a workflow through GitHub REST; mutable action requires explicit approval."""
        body={"ref":ref}
        if inputs:
            body["inputs"]=inputs
        return self.request("POST",f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",capability="actions.write",approved=approved,body=body)
    def releases(self, owner, repo): return self.request("GET",f"/repos/{owner}/{repo}/releases",capability="releases.read")
    def search(self, query, search_type="repositories"): return self.request("GET",f"/search/{search_type}",capability="search.read",params={"q":query})
    def capability_catalog(self):
        return {"ok":True,"gateway":"GitHubControlPlane","configured":self.configured(),"domains":["repositories","git-data","contents","branches","tags","commits","issues","pull-requests","reviews","actions","releases","packages","projects","security","search","users","organizations","webhooks"],"execution_model":["discover","authorize","execute","verify","audit"],"write_policy":"explicit approval for mutable operations"}

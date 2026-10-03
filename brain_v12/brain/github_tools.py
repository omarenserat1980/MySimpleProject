from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class BrainGitHubTools:
    """Allowlisted GitHub REST tools for Brain Tool Calling.

    Uses the server-side token only; never exposes the token to the model.
    Read tools are low-risk. Mutations are high-risk and must pass Brain approval.
    """

    def __init__(self, repository: Optional[str] = None):
        self.repository = repository or os.getenv("BRAIN_GITHUB_REPOSITORY") or os.getenv("GITHUB_REPOSITORY") or "omarenserat1980/MySimpleProject"

    def _token(self) -> str:
        token = os.getenv("BRAIN_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN_NOT_CONFIGURED")
        return token

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> Any:
        req = urllib.request.Request(
            "https://api.github.com" + path,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self._token(),
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Electronic-Brain-GitHub-ToolCalling",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"GITHUB_HTTP_{exc.code}:{detail}")

    def _repo(self, params: Dict[str, Any]) -> str:
        repo = str(params.get("repository") or self.repository).strip()
        if repo.count("/") != 1:
            raise ValueError("INVALID_REPOSITORY")
        return repo

    def status(self, _: Dict[str, Any]) -> Dict[str, Any]:
        data = self._request("GET", "/repos/" + self.repository)
        return {"repository": data.get("full_name"), "default_branch": data.get("default_branch"), "permissions": data.get("permissions", {})}

    def get_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        path = urllib.parse.quote(str(params["path"]).strip().lstrip("/"), safe="/")
        query = {"ref": str(params.get("ref") or params.get("branch") or "main")}
        data = self._request("GET", f"/repos/{repo}/contents/{path}?{urllib.parse.urlencode(query)}")
        raw = data.get("content", "")
        content = base64.b64decode(raw.replace("\n", "")).decode("utf-8") if raw else ""
        return {"path": data.get("path"), "sha": data.get("sha"), "content": content, "html_url": data.get("html_url")}

    def list_issues(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        query = urllib.parse.urlencode({"state": params.get("state", "open"), "per_page": min(int(params.get("per_page", 50)), 100)})
        data = self._request("GET", f"/repos/{repo}/issues?{query}")
        return {"issues": [{"number": x["number"], "title": x["title"], "state": x["state"], "html_url": x.get("html_url"), "pull_request": bool(x.get("pull_request"))} for x in data]}

    def list_pulls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        query = urllib.parse.urlencode({"state": params.get("state", "open"), "per_page": min(int(params.get("per_page", 50)), 100)})
        data = self._request("GET", f"/repos/{repo}/pulls?{query}")
        return {"pull_requests": [{"number": x["number"], "title": x["title"], "state": x["state"], "draft": x.get("draft", False), "head": (x.get("head") or {}).get("ref"), "base": (x.get("base") or {}).get("ref"), "html_url": x.get("html_url")} for x in data]}

    def get_actions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        query = urllib.parse.urlencode({"per_page": min(int(params.get("per_page", 30)), 100)})
        data = self._request("GET", f"/repos/{repo}/actions/runs?{query}")
        return {"runs": [{"id": x["id"], "name": x["name"], "status": x["status"], "conclusion": x.get("conclusion"), "branch": x.get("head_branch"), "sha": x.get("head_sha"), "html_url": x.get("html_url")} for x in data.get("workflow_runs", [])]}

    def create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        payload = {"title": str(params["title"]), "body": str(params.get("body", ""))}
        if params.get("labels"): payload["labels"] = list(params["labels"])
        data = self._request("POST", f"/repos/{repo}/issues", payload)
        return {"number": data.get("number"), "html_url": data.get("html_url"), "state": data.get("state"), "title": data.get("title")}

    def comment_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        number = int(params["issue_number"])
        data = self._request("POST", f"/repos/{repo}/issues/{number}/comments", {"body": str(params["body"])})
        return {"comment_id": data.get("id"), "html_url": data.get("html_url")}

    def create_branch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        branch = str(params["branch"]).strip()
        base = str(params.get("sha") or params.get("base_ref") or "main")
        if len(base) != 40:
            ref = self._request("GET", f"/repos/{repo}/git/ref/heads/{urllib.parse.quote(base, safe='')}")
            base = ref["object"]["sha"]
        data = self._request("POST", f"/repos/{repo}/git/refs", {"ref": "refs/heads/" + branch, "sha": base})
        return {"branch": branch, "sha": (data.get("object") or {}).get("sha"), "ref": data.get("ref")}

    def create_or_update_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        path = urllib.parse.quote(str(params["path"]).strip().lstrip("/"), safe="/")
        branch = str(params.get("branch") or "main")
        payload = {"message": str(params.get("message") or "brain: tool-calling file update"), "content": base64.b64encode(str(params["content"]).encode()).decode(), "branch": branch}
        if params.get("sha"):
            payload["sha"] = str(params["sha"])
        data = self._request("PUT", f"/repos/{repo}/contents/{path}", payload)
        return {"commit_sha": (data.get("commit") or {}).get("sha"), "content_sha": (data.get("content") or {}).get("sha"), "path": str(params["path"])}

    def delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        path = urllib.parse.quote(str(params["path"]).strip().lstrip("/"), safe="/")
        payload = {"message": str(params.get("message") or "brain: tool-calling file deletion"), "sha": str(params["sha"]), "branch": str(params.get("branch") or "main")}
        data = self._request("DELETE", f"/repos/{repo}/contents/{path}", payload)
        return {"commit_sha": (data.get("commit") or {}).get("sha"), "path": str(params["path"])}

    def merge_pull_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        repo = self._repo(params)
        number = int(params["pull_number"])
        payload = {"merge_method": str(params.get("merge_method") or "squash")}
        data = self._request("PUT", f"/repos/{repo}/pulls/{number}/merge", payload)
        return {"merged": data.get("merged", False), "message": data.get("message"), "sha": data.get("sha")}

    def register(self, brain_ai) -> None:
        brain_ai.register_tool("github.status", "Read GitHub repository status and permissions.", self.status, risk="low")
        brain_ai.register_tool("github.get_file", "Read a UTF-8 repository file.", self.get_file, risk="low")
        brain_ai.register_tool("github.list_issues", "List repository issues.", self.list_issues, risk="low")
        brain_ai.register_tool("github.list_pull_requests", "List pull requests.", self.list_pulls, risk="low")
        brain_ai.register_tool("github.actions", "Read recent GitHub Actions runs.", self.get_actions, risk="low")
        brain_ai.register_tool("github.create_issue", "Create a GitHub issue.", self.create_issue, risk="high", permission="github_write")
        brain_ai.register_tool("github.comment_issue", "Comment on an issue or pull request.", self.comment_issue, risk="high", permission="github_write")
        brain_ai.register_tool("github.create_branch", "Create a Git branch.", self.create_branch, risk="high", permission="github_write")
        brain_ai.register_tool("github.write_file", "Create or update a repository file.", self.create_or_update_file, risk="high", permission="github_write")
        brain_ai.register_tool("github.delete_file", "Delete a repository file.", self.delete_file, risk="high", permission="github_write")
        brain_ai.register_tool("github.merge_pull_request", "Merge a pull request.", self.merge_pull_request, risk="high", permission="github_merge")

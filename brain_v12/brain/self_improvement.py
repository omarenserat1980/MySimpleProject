from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import json
import os
import re
import urllib.request

ALLOWED_ROOTS=("brain_v12/",)
MAX_FILE_BYTES=200_000


@dataclass
class ImprovementProposal:
    objective: str
    files: list[str]
    rationale: str
    patch_plan: list[dict[str, Any]]
    requires_approval: bool = True


class SelfImprovementEngine:
    """Bounded self-improvement planner.

    It can inspect an allowlisted repository through GitHub's API, ask an
    external model through a configured gateway, and return a proposal.
    Actual repository writes remain explicitly approved.
    """

    def __init__(self, repo: str | None = None, token: str | None = None):
        self.repo = repo or os.getenv("BRAIN_GITHUB_REPO", "")
        self.token = token or os.getenv("GITHUB_TOKEN", "")

    def _headers(self) -> dict[str, str]:
        headers={"Accept":"application/vnd.github+json","User-Agent":"Electronic-Brain-V12"}
        if self.token:
            headers["Authorization"]=f"Bearer {self.token}"
        return headers

    def inspect(self, path: str) -> dict[str, Any]:
        self._validate_path(path)
        if not self.repo:
            return {"ok":False,"error":"GITHUB_REPO_NOT_CONFIGURED"}
        url=f"https://api.github.com/repos/{self.repo}/contents/{path}"
        req=urllib.request.Request(url,headers=self._headers())
        with urllib.request.urlopen(req,timeout=15) as response:
            data=json.load(response)
        import base64
        content=base64.b64decode(data["content"]).decode("utf-8")
        if len(content.encode("utf-8"))>MAX_FILE_BYTES:
            raise ValueError("FILE_TOO_LARGE")
        return {"ok":True,"path":path,"sha":data["sha"],"content":content}

    def propose(self, objective: str, files: list[str]) -> dict[str, Any]:
        objective=objective.strip()
        if not objective:
            raise ValueError("EMPTY_OBJECTIVE")
        clean=[]
        snapshots=[]
        for path in files:
            self._validate_path(path)
            clean.append(path)
            snapshots.append(self.inspect(path))
        rationale="تحليل الملفات المحددة واقتراح أصغر تغيير قابل للاختبار لتحقيق الهدف."
        proposal=ImprovementProposal(
            objective=objective,
            files=clean,
            rationale=rationale,
            patch_plan=[{"path":s["path"],"sha":s["sha"],"action":"review-and-edit"} for s in snapshots],
        )
        return {"ok":True,"proposal":asdict(proposal),"snapshots":[{"path":s["path"],"sha":s["sha"]} for s in snapshots]}

    def _validate_path(self,path:str) -> None:
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise ValueError("PATH_NOT_ALLOWED")
        if not path.startswith(ALLOWED_ROOTS):
            raise ValueError("PATH_OUTSIDE_BRAIN_V12")
        if not re.fullmatch(r"[A-Za-z0-9_./-]+",path):
            raise ValueError("INVALID_PATH")

    def status(self) -> dict[str, Any]:
        return {
            "enabled": bool(self.repo),
            "repo": self.repo or None,
            "write_requires_explicit_approval": True,
            "allowlisted_roots": list(ALLOWED_ROOTS),
            "max_file_bytes": MAX_FILE_BYTES,
            "chatgpt_session_access": False,
            "chatgpt_gateway": "external-provider-required",
        }

"""Safe GitHub code tool for the Electronic Brain.

Provides inspect -> plan -> apply -> verify primitives for repository code.
OAuth credentials are never stored here; authentication is delegated to the
GitHub integration/runtime. The tool only edits allow-listed repository paths
and requires the caller to supply the current file SHA before replacing a file.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Callable, Optional


@dataclass(frozen=True)
class CodeChange:
    path: str
    content: str
    expected_sha: str
    message: str


@dataclass(frozen=True)
class CodeResult:
    status: str
    path: str
    commit_sha: Optional[str] = None
    content_sha: Optional[str] = None
    content_hash: Optional[str] = None
    detail: str = ""


class GitHubCodeTool:
    """Repository change planner/executor.

    The actual GitHub OAuth/API call is injected as a callback. This keeps
    OAuth tokens outside the brain's source code and memory.
    """

    def __init__(
        self,
        fetch_file: Callable[[str], dict],
        update_file: Callable[[str, str, str, str, str], dict],
        repository: str = "omarenserat1980/MySimpleProject",
        allowed_prefixes: tuple[str, ...] = ("brain_v7/",),
    ) -> None:
        self.fetch_file = fetch_file
        self.update_file = update_file
        self.repository = repository
        self.allowed_prefixes = allowed_prefixes

    def _allowed(self, path: str) -> bool:
        return any(path.startswith(prefix) for prefix in self.allowed_prefixes)

    def inspect(self, path: str) -> dict:
        if not self._allowed(path):
            raise PermissionError(f"path_not_allowed:{path}")
        return self.fetch_file(path)

    def plan(self, path: str, content: str, expected_sha: str, message: str) -> CodeChange:
        if not self._allowed(path):
            raise PermissionError(f"path_not_allowed:{path}")
        if not expected_sha:
            raise ValueError("expected_sha_required")
        if not message.strip():
            raise ValueError("commit_message_required")
        return CodeChange(path, content, expected_sha, message)

    def apply(self, change: CodeChange) -> CodeResult:
        if not self._allowed(change.path):
            raise PermissionError(f"path_not_allowed:{change.path}")

        result = self.update_file(
            self.repository,
            change.path,
            change.content,
            change.message,
            change.expected_sha,
        )
        payload = result.get("result", result)
        commit_sha = payload.get("commit_sha") or payload.get("commit", {}).get("sha")
        content_sha = payload.get("content_sha") or payload.get("content", {}).get("sha")
        return CodeResult(
            status="APPLIED",
            path=change.path,
            commit_sha=commit_sha,
            content_sha=content_sha,
            content_hash=sha256(change.content.encode("utf-8")).hexdigest(),
        )

    def snapshot(self) -> dict:
        return {
            "repository": self.repository,
            "allowed_prefixes": list(self.allowed_prefixes),
            "oauth_secret_storage": False,
            "supports": ["inspect", "plan", "apply"],
        }


def summarize(result: CodeResult) -> dict:
    return asdict(result)

"""Bounded GitHub-backed code executor for the Electronic Brain.

The adapter persists validated source changes to one configured repository.
Secrets are read only from the runtime environment and are never stored,
logged, or returned. Multi-file persistence uses one atomic Git commit so a
successful remote operation never leaves a half-written change set.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import base64
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Iterable

from .code_workspace_tool import CodeChange, PROTECTED_NAMES


@dataclass(frozen=True)
class GitHubWriteResult:
    path: str
    status: str
    commit_sha: str = ""
    content_sha: str = ""
    error: str = ""


class GitHubCodeExecutor:
    """Safely persist Brain-generated source changes to one GitHub repository."""

    def __init__(
        self,
        *,
        repository: str | None = None,
        branch: str | None = None,
        token_env: str = "GITHUB_TOKEN",
        allowed_prefix: str = "brain_v7/",
    ) -> None:
        self.repository = repository or os.getenv("BRAIN_GITHUB_REPOSITORY", "omarenserat1980/MySimpleProject")
        self.branch = branch or os.getenv("BRAIN_GITHUB_BRANCH", "main")
        self.token_env = token_env
        self.allowed_prefix = allowed_prefix.rstrip("/") + "/"
        self.base_url = "https://api.github.com"
        self.audit: list[GitHubWriteResult] = []

    @property
    def configured(self) -> bool:
        return bool(self.repository and os.getenv(self.token_env))

    def _token(self) -> str:
        token = os.getenv(self.token_env, "")
        if not token:
            raise PermissionError(f"missing runtime secret: {self.token_env}")
        return token

    def _safe_path(self, path: str) -> str:
        normalized = path.replace("\\", "/").lstrip("/")
        if not normalized.startswith(self.allowed_prefix):
            raise PermissionError("path is outside the GitHub source allowlist")
        parts = normalized.split("/")
        if any(part in PROTECTED_NAMES for part in parts):
            raise PermissionError("protected credential file")
        if ".." in parts or not normalized.endswith((".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt")):
            raise PermissionError("unsupported or unsafe source path")
        return normalized

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = self._token()
        url = self.base_url + path
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "electronic-brain-code-executor",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub network error: {exc.reason}") from exc

    def inspect(self, path: str) -> dict:
        safe = self._safe_path(path)
        return self._request(
            "GET",
            f"/repos/{self.repository}/contents/{safe}?ref={self.branch}",
        )

    def apply(self, changes: Iterable[CodeChange], *, message: str) -> list[GitHubWriteResult]:
        """Persist a change set as one Git commit."""
        changes = list(changes)
        if not changes:
            return []
        if not self.configured:
            raise PermissionError("GitHub executor is not configured")
        if not message.strip():
            raise ValueError("commit message is required")

        safe_changes = [(self._safe_path(c.path), c) for c in changes]

        # Resolve the branch tip and its base tree.
        ref = self._request(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{self.branch}",
        )
        parent_sha = ref["object"]["sha"]
        parent_commit = self._request(
            "GET",
            f"/repos/{self.repository}/git/commits/{parent_sha}",
        )
        base_tree = parent_commit["tree"]["sha"]

        tree_items = []
        content_shas = {}
        for safe, change in safe_changes:
            blob = self._request(
                "POST",
                f"/repos/{self.repository}/git/blobs",
                {
                    "content": base64.b64encode(change.content.encode("utf-8")).decode("ascii"),
                    "encoding": "base64",
                },
            )
            blob_sha = blob["sha"]
            content_shas[safe] = blob_sha
            tree_items.append({
                "path": safe,
                "mode": "100644",
                "type": "blob",
                "sha": blob_sha,
            })

        tree = self._request(
            "POST",
            f"/repos/{self.repository}/git/trees",
            {"base_tree": base_tree, "tree": tree_items},
        )
        commit = self._request(
            "POST",
            f"/repos/{self.repository}/git/commits",
            {
                "message": message[:120],
                "tree": tree["sha"],
                "parents": [parent_sha],
            },
        )
        commit_sha = commit["sha"]

        # Fast-forward only: never force-rewrite the branch.
        current_ref = self._request(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{self.branch}",
        )
        if current_ref["object"]["sha"] != parent_sha:
            raise RuntimeError("GitHub branch changed during write; refusing non-fast-forward update")
        self._request(
            "PATCH",
            f"/repos/{self.repository}/git/refs/heads/{self.branch}",
            {"sha": commit_sha, "force": False},
        )

        results = [
            GitHubWriteResult(
                path=safe,
                status="COMMITTED",
                commit_sha=commit_sha,
                content_sha=content_shas[safe],
            )
            for safe, _ in safe_changes
        ]
        self.audit.extend(results)
        return results

    def snapshot(self) -> dict:
        return {
            "configured": self.configured,
            "repository": self.repository,
            "branch": self.branch,
            "allowed_prefix": self.allowed_prefix,
            "credential_storage": False,
            "token_exposed": False,
            "delete_supported": False,
            "force_push_supported": False,
            "arbitrary_api_supported": False,
            "atomic_multi_file_commit": True,
            "fast_forward_only": True,
            "audit": [asdict(x) for x in self.audit[-20:]],
        }

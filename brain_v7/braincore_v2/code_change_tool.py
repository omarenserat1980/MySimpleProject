"""Safe repository change tool for the Electronic Brain.

This module gives the brain an explicit, auditable interface for proposing,
validating, and applying code changes. It never stores credentials and it
cannot execute arbitrary shell commands.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import PurePosixPath
from typing import Optional


ALLOWED_PREFIXES = ("brain_v7/braincore_v2/",)
BLOCKED_NAMES = {".env", "credentials.json", "secrets.json", "token.json"}


@dataclass(frozen=True)
class CodeChange:
    path: str
    content: str
    expected_sha256: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class ChangeResult:
    status: str
    path: str
    content_sha256: str
    reason: str


class CodeChangeTool:
    """Policy-aware code storage/change planner.

    The actual GitHub API call remains an integration concern. This class
    validates a proposed change and produces a deterministic change record.
    """

    def validate(self, change: CodeChange) -> None:
        path = PurePosixPath(change.path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("unsafe repository path")
        if not any(change.path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            raise ValueError("path outside brain_v7/braincore_v2 is not allowed")
        if path.name in BLOCKED_NAMES:
            raise ValueError("credential/secret files are blocked")
        if len(change.content.encode("utf-8")) > 1_000_000:
            raise ValueError("change is too large")
        if not change.reason.strip():
            raise ValueError("change reason is required")

    def fingerprint(self, content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

    def prepare(self, change: CodeChange) -> dict:
        self.validate(change)
        digest = self.fingerprint(change.content)
        return {
            "path": change.path,
            "content_sha256": digest,
            "expected_sha256": change.expected_sha256,
            "reason": change.reason,
            "action": "UPDATE_OR_CREATE",
        }

    def result(self, change: CodeChange, status: str = "PREPARED") -> ChangeResult:
        self.validate(change)
        return ChangeResult(
            status=status,
            path=change.path,
            content_sha256=self.fingerprint(change.content),
            reason=change.reason,
        )

    def snapshot(self) -> dict:
        return {
            "allowed_prefixes": list(ALLOWED_PREFIXES),
            "blocked_names": sorted(BLOCKED_NAMES),
            "credential_storage": False,
            "arbitrary_shell_execution": False,
        }

from __future__ import annotations

from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class PermissionGrant:
    action: str
    actor: str
    reason: str
    granted_at: float


class PermissionPolicy:
    """Explicit in-memory grants; all ungranted actions are denied by default."""

    def __init__(self) -> None:
        self._grants: dict[tuple[str, str], PermissionGrant] = {}

    def grant(self, action: str, actor: str, reason: str) -> PermissionGrant:
        if not action.strip() or not actor.strip() or not reason.strip():
            raise ValueError("action, actor, and reason are required")
        grant = PermissionGrant(action, actor, reason, time())
        self._grants[(action, actor)] = grant
        return grant

    def revoke(self, action: str, actor: str) -> bool:
        return self._grants.pop((action, actor), None) is not None

    def is_allowed(self, action: str, actor: str) -> bool:
        return (action, actor) in self._grants

    def require(self, action: str, actor: str) -> None:
        if not self.is_allowed(action, actor):
            raise PermissionError(f"permission denied for action: {action}")

    def is_ready(self) -> bool:
        return isinstance(self._grants, dict)

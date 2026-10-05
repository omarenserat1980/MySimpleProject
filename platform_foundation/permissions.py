from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionRisk(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    IRREVERSIBLE = "IRREVERSIBLE"


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    action: str
    risk: ActionRisk
    reason: str


class PermissionBoundary:
    """Explicit allowlist; unknown actions are denied by default."""

    def __init__(self, allowed: dict[str, ActionRisk] | None = None) -> None:
        self._allowed = dict(allowed or {})

    def decide(self, action: str, risk: ActionRisk, *, explicit_approval: bool = False) -> PermissionDecision:
        if not action:
            return PermissionDecision(False, action, risk, "action is required")
        configured = self._allowed.get(action)
        if configured is None:
            return PermissionDecision(False, action, risk, "action is not allowlisted")
        if configured != risk:
            return PermissionDecision(False, action, risk, "risk level mismatch")
        if risk is ActionRisk.IRREVERSIBLE and not explicit_approval:
            return PermissionDecision(False, action, risk, "irreversible actions require an explicit higher-level approval")
        return PermissionDecision(True, action, risk, "allowlisted with explicit approval" if risk is ActionRisk.IRREVERSIBLE else "allowlisted")

    def is_ready(self) -> bool:
        return all(isinstance(k, str) and isinstance(v, ActionRisk) for k, v in self._allowed.items())

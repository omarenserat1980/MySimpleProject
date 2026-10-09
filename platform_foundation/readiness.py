from __future__ import annotations

from dataclasses import dataclass

from .audit_chain import AuditChain
from .permissions import PermissionBoundary
from .persistent_state import SQLiteStateStore


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, bool]


class ReadinessGate:
    """Conservative readiness check for the independent foundation."""

    def __init__(
        self,
        state: SQLiteStateStore,
        audit: AuditChain,
        permissions: PermissionBoundary,
    ) -> None:
        self.state = state
        self.audit = audit
        self.permissions = permissions

    def check(self) -> ReadinessReport:
        checks = {
            "state_store": self.state.is_ready(),
            "audit_chain": self.audit.verify(),
            "permission_boundary": self.permissions.is_ready(),
        }
        return ReadinessReport(ready=all(checks.values()), checks=checks)


__all__ = ["ReadinessGate", "ReadinessReport"]

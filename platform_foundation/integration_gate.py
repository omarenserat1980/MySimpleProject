from __future__ import annotations

from dataclasses import dataclass

from .audit_chain import AuditChain
from .permissions import PermissionBoundary
from .persistent_state import SQLiteStateStore
from .readiness import ReadinessGate


@dataclass(frozen=True)
class IntegrationAdmission:
    admitted: bool
    reason: str
    checks: dict[str, bool]


class IntegrationGate:
    """Require a healthy independent foundation before higher-level integration."""

    def __init__(
        self,
        state: SQLiteStateStore,
        audit: AuditChain,
        permissions: PermissionBoundary,
    ) -> None:
        self.readiness = ReadinessGate(state, audit, permissions)

    def admit(self) -> IntegrationAdmission:
        report = self.readiness.check()
        if not report.ready:
            return IntegrationAdmission(
                admitted=False,
                reason="foundation readiness gate failed",
                checks=report.checks,
            )
        return IntegrationAdmission(
            admitted=True,
            reason="foundation ready for higher-level integration",
            checks=report.checks,
        )


__all__ = ["IntegrationAdmission", "IntegrationGate"]

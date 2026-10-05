from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from platform_foundation.audit_chain import AuditChain
from platform_foundation.integration_gate import IntegrationGate
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from brain_v12.brain.brain_supervisor import BrainSupervisor


@dataclass(frozen=True)
class BrainAdmissionResult:
    admitted: bool
    reason: str
    checks: dict[str, bool]


class BrainSupervisorBridge:
    """Admission-controlled bridge from the independent foundation to Brain Supervisor."""

    def __init__(
        self,
        state: SQLiteStateStore,
        audit: AuditChain,
        permissions: PermissionBoundary,
        *,
        root: str,
        max_cycles: int = 5,
    ) -> None:
        self.gate = IntegrationGate(state, audit, permissions)
        self.supervisor = BrainSupervisor(root=root, max_cycles=max_cycles)

    def admit(self) -> BrainAdmissionResult:
        result = self.gate.admit()
        return BrainAdmissionResult(result.admitted, result.reason, result.checks)

    def create_job(self, task: str, *, steps: list[str] | None = None) -> Any:
        admission = self.admit()
        if not admission.admitted:
            raise RuntimeError(f"brain integration blocked: {admission.reason}")
        return self.supervisor.create(task, steps=steps)

    def simulate_verified_path(self, task: str) -> Any:
        admission = self.admit()
        if not admission.admitted:
            raise RuntimeError(f"brain integration blocked: {admission.reason}")
        return self.supervisor.run_simulation(task, verification_ok=True)


__all__ = ["BrainAdmissionResult", "BrainSupervisorBridge"]

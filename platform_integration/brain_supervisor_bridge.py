from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from platform_foundation.audit_chain import AuditChain
from platform_foundation.integration_gate import IntegrationGate
from platform_foundation.permissions import ActionRisk, PermissionBoundary
from platform_foundation.persistent_state import SQLiteStateStore
from platform_foundation.supervisor import Supervisor
from platform_foundation.verification import VerificationGate
from brain_v12.brain.brain_supervisor import BrainSupervisor


@dataclass(frozen=True)
class BrainAdmissionResult:
    admitted: bool
    reason: str
    checks: dict[str, bool]


@dataclass(frozen=True)
class BrainVerifiedExecution:
    task_id: str
    executed: bool
    verified: bool
    status: str
    attempts: int
    output: Any = None
    error: str | None = None


class BrainSupervisorBridge:
    """Admission-controlled bridge from the independent foundation to Brain Supervisor.

    Higher-level Brain orchestration is admitted only after the independent foundation
    is healthy. Executions that cross this bridge also require an independent verifier
    before they can be reported as verified.
    """

    def __init__(
        self,
        state: SQLiteStateStore,
        audit: AuditChain,
        permissions: PermissionBoundary,
        *,
        root: str,
        max_cycles: int = 5,
    ) -> None:
        self.state = state
        self.audit = audit
        self.permissions = permissions
        self.gate = IntegrationGate(state, audit, permissions)
        self.supervisor = BrainSupervisor(root=root, max_cycles=max_cycles)
        self.execution = Supervisor(state, audit, permissions)
        self.verification = VerificationGate(state, audit)

    def admit(self) -> BrainAdmissionResult:
        result = self.gate.admit()
        return BrainAdmissionResult(result.admitted, result.reason, result.checks)

    def _require_admission(self) -> None:
        admission = self.admit()
        if not admission.admitted:
            raise RuntimeError(f"brain integration blocked: {admission.reason}")

    def create_job(self, task: str, *, steps: list[str] | None = None) -> Any:
        self._require_admission()
        return self.supervisor.create(task, steps=steps)

    def simulate_verified_path(self, task: str) -> Any:
        self._require_admission()
        return self.supervisor.run_simulation(task, verification_ok=True)

    def execute_verified(
        self,
        task_id: str,
        action: str,
        risk: ActionRisk,
        handler: Callable[[], Any],
        verifier: Callable[[Any], bool],
        *,
        max_attempts: int = 3,
    ) -> BrainVerifiedExecution:
        """Execute through foundation controls, then independently verify the result."""
        self._require_admission()
        self.execution.register(
            task_id,
            action,
            risk,
            handler,
            max_attempts=max_attempts,
        )
        result = self.execution.run(task_id)
        if not result.allowed or result.status.value != "SUCCESS":
            self.audit.record(
                "brain.bridge.execution_failed",
                {"task_id": task_id, "status": result.status.value, "error": result.error},
            )
            return BrainVerifiedExecution(
                task_id, False, False, result.status.value, result.attempts,
                output=result.output, error=result.error,
            )

        verified = self.verification.verify(task_id, result.output, verifier)
        status = verified.status.value
        self.state.set(
            f"brain_bridge:{task_id}",
            {
                "task_id": task_id,
                "executed": True,
                "verified": verified.verified,
                "status": status,
                "attempts": result.attempts,
                "error": verified.error,
            },
        )
        self.audit.record(
            "brain.bridge.verification_gate",
            {
                "task_id": task_id,
                "executed": True,
                "verified": verified.verified,
                "status": status,
            },
        )
        return BrainVerifiedExecution(
            task_id, True, verified.verified, status, result.attempts,
            output=result.output, error=verified.error,
        )

    def load_verified_execution(self, task_id: str) -> BrainVerifiedExecution | None:
        """Load only a durably persisted execution that passed the verification gate."""
        record = self.state.get(f"brain_bridge:{task_id}")
        verification = self.state.get(f"verification:{task_id}")
        if not record or not verification:
            return None
        if not (
            record.get("executed") is True
            and record.get("verified") is True
            and record.get("status") == "SUCCESS"
            and verification.get("verified") is True
            and verification.get("status") == "SUCCESS"
        ):
            return None
        return BrainVerifiedExecution(
            task_id=task_id,
            executed=True,
            verified=True,
            status="SUCCESS",
            attempts=int(record.get("attempts", 0)),
            error=record.get("error"),
        )


__all__ = ["BrainAdmissionResult", "BrainVerifiedExecution", "BrainSupervisorBridge"]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .audit_chain import AuditChain
from .permissions import ActionRisk, PermissionBoundary
from .persistent_state import SQLiteStateStore
from .recovery import RecoveryRunner
from .task_state import TaskStatus


@dataclass(frozen=True)
class SupervisorResult:
    task_id: str
    status: TaskStatus
    allowed: bool
    attempts: int
    output: Any = None
    error: str | None = None


class Supervisor:
    """Evidence-driven execution supervisor for authorized tasks."""

    def __init__(
        self,
        state: SQLiteStateStore,
        audit: AuditChain,
        permissions: PermissionBoundary,
    ) -> None:
        self.state = state
        self.audit = audit
        self.permissions = permissions
        self.recovery = RecoveryRunner(state, audit)

    def register(
        self,
        task_id: str,
        action: str,
        risk: ActionRisk,
        handler: Callable[[], Any],
        *,
        max_attempts: int = 3,
        retryable: Callable[[Exception], bool] | None = None,
    ) -> None:
        self.state.set(
            f"supervisor:{task_id}",
            {
                "task_id": task_id,
                "action": action,
                "risk": risk.value,
                "status": TaskStatus.PENDING.value,
                "max_attempts": max_attempts,
            },
        )
        self.state.set(
            f"handler:{task_id}",
            {"registered": True},
        )
        # Handlers are process-local by design; durable state never stores executable code.
        setattr(self, f"_handler_{task_id}", (handler, retryable))
        self.audit.record(
            "task.registered",
            {"task_id": task_id, "action": action, "risk": risk.value},
        )

    def run(self, task_id: str) -> SupervisorResult:
        record = self.state.get(f"supervisor:{task_id}")
        if record is None:
            error = "task is not registered"
            self.audit.record("task.supervisor_failed", {"task_id": task_id, "error": error})
            return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=error)

        decision = self.permissions.decide(record["action"], ActionRisk(record["risk"]))
        if not decision.allowed:
            self.state.set(
                f"supervisor:{task_id}",
                {**record, "status": TaskStatus.FAILED.value, "error": decision.reason},
            )
            self.audit.record(
                "task.permission_denied",
                {"task_id": task_id, "reason": decision.reason},
            )
            return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=decision.reason)

        self.state.set(
            f"supervisor:{task_id}",
            {**record, "status": TaskStatus.RUNNING.value},
        )
        self.audit.record("task.execution_started", {"task_id": task_id})

        handler, retryable = getattr(self, f"_handler_{task_id}", (None, None))
        if handler is None:
            error = "execution handler is unavailable"
            self.state.set(
                f"supervisor:{task_id}",
                {**record, "status": TaskStatus.FAILED.value, "error": error},
            )
            self.audit.record("task.supervisor_failed", {"task_id": task_id, "error": error})
            return SupervisorResult(task_id, TaskStatus.FAILED, True, 0, error=error)

        result = self.recovery.run(
            task_id,
            handler,
            max_attempts=int(record["max_attempts"]),
            retryable=retryable,
        )
        final_record = self.state.get(f"supervisor:{task_id}") or record
        self.state.set(
            f"supervisor:{task_id}",
            {
                **final_record,
                "status": result.status.value,
                "error": result.error,
            },
        )
        self.audit.record(
            "task.execution_verified",
            {
                "task_id": task_id,
                "status": result.status.value,
                "attempts": result.attempts,
            },
        )
        return SupervisorResult(
            task_id,
            result.status,
            True,
            result.attempts,
            output=result.output,
            error=result.error,
        )


__all__ = ["Supervisor", "SupervisorResult"]

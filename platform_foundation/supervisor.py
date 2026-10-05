from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from .audit_chain import AuditChain
from .authority import AuthorityApprovalLedger
from .lease import TaskLease
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
        authority: AuthorityApprovalLedger | None = None,
    ) -> None:
        self.state = state
        self.audit = audit
        self.permissions = permissions
        self.authority = authority
        self.recovery = RecoveryRunner(state, audit)
        self.lease = TaskLease(state, audit)
        self.owner = f"supervisor:{uuid.uuid4().hex}"

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
        self.state.set(f"handler:{task_id}", {"registered": True})
        setattr(self, f"_handler_{task_id}", (handler, retryable))
        self.audit.record(
            "task.registered",
            {"task_id": task_id, "action": action, "risk": risk.value},
        )

    def run(self, task_id: str, *, lease_ttl_seconds: float = 60.0) -> SupervisorResult:
        record = self.state.get(f"supervisor:{task_id}")
        if record is None:
            error = "task is not registered"
            self.audit.record("task.supervisor_failed", {"task_id": task_id, "error": error})
            return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=error)

        requested_risk = ActionRisk(record["risk"])
        approval = None
        if requested_risk is ActionRisk.IRREVERSIBLE:
            if self.authority is None:
                decision = self.permissions.decide(record["action"], requested_risk)
            else:
                approval = self.authority.check(task_id, record["action"], requested_risk)
                decision = self.permissions.decide(record["action"], requested_risk, explicit_approval=approval.approved)
        else:
            decision = self.permissions.decide(record["action"], requested_risk)
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

        if requested_risk is ActionRisk.IRREVERSIBLE and (approval is None or not approval.approved):
            self.state.set(f"supervisor:{task_id}", {**record, "status": TaskStatus.FAILED.value, "error": decision.reason})
            self.audit.record("task.authority_denied", {"task_id": task_id, "reason": decision.reason})
            return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=decision.reason)

        lease = self.lease.acquire(task_id, self.owner, ttl_seconds=lease_ttl_seconds)
        if not lease.acquired:
            error = "task lease unavailable"
            self.audit.record(
                "task.lease_denied",
                {"task_id": task_id, "owner": self.owner},
            )
            return SupervisorResult(task_id, TaskStatus.FAILED, True, 0, error=error)

        try:
            if requested_risk is ActionRisk.IRREVERSIBLE:
                consumed = self.authority.consume(task_id, record["action"], requested_risk)
                if not consumed.approved:
                    self.state.set(f"supervisor:{task_id}", {**record, "status": TaskStatus.FAILED.value, "error": consumed.reason})
                    self.audit.record("task.authority_denied", {"task_id": task_id, "reason": consumed.reason})
                    return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=consumed.reason)
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

            lease_lost = threading.Event()
            stop_heartbeat = threading.Event()
            interval = max(0.05, min(5.0, lease_ttl_seconds / 3.0))

            def heartbeat_loop() -> None:
                while not stop_heartbeat.wait(interval):
                    beat = self.lease.heartbeat(task_id, self.owner, ttl_seconds=lease_ttl_seconds)
                    if not beat.acquired:
                        lease_lost.set()
                        return

            heartbeat_thread = threading.Thread(target=heartbeat_loop, name=f"lease-heartbeat:{task_id}", daemon=True)
            heartbeat_thread.start()
            try:
                result = self.recovery.run(
                    task_id,
                    handler,
                    max_attempts=int(record["max_attempts"]),
                    retryable=retryable,
                )
            finally:
                stop_heartbeat.set()
                heartbeat_thread.join(timeout=max(1.0, interval * 2))

            if lease_lost.is_set() or not self.lease.is_owned(task_id, self.owner):
                error = "execution lease lost"
                self.state.set(
                    f"supervisor:{task_id}",
                    {**record, "status": TaskStatus.FAILED.value, "error": error},
                )
                self.audit.record("task.lease_lost", {"task_id": task_id, "owner": self.owner})
                return SupervisorResult(task_id, TaskStatus.FAILED, True, result.attempts, error=error)
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
        finally:
            self.lease.release(task_id, self.owner)


__all__ = ["Supervisor", "SupervisorResult"]

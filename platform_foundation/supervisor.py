from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from .audit_chain import AuditChain
from .authority import AuthorityApprovalLedger
from .lease import TaskLease
from .permissions import ActionRisk, PermissionBoundary
from .persistent_state import SQLiteStateStore
from .recovery import RecoveryRunner
from .task_state import TaskStatus


class SupervisorPhase(str, Enum):
    DISCOVER = "DISCOVER"
    PLAN = "PLAN"
    SELECT = "SELECT"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    RETRY = "RETRY"
    DELIVER = "DELIVER"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


_PHASE_ORDER = {
    SupervisorPhase.DISCOVER: {SupervisorPhase.PLAN, SupervisorPhase.BLOCKED},
    SupervisorPhase.PLAN: {SupervisorPhase.SELECT, SupervisorPhase.BLOCKED},
    SupervisorPhase.SELECT: {SupervisorPhase.EXECUTE, SupervisorPhase.BLOCKED},
    SupervisorPhase.EXECUTE: {SupervisorPhase.VERIFY, SupervisorPhase.REPAIR, SupervisorPhase.RETRY, SupervisorPhase.FAILED},
    SupervisorPhase.VERIFY: {SupervisorPhase.DELIVER, SupervisorPhase.REPAIR, SupervisorPhase.RETRY, SupervisorPhase.FAILED},
    SupervisorPhase.REPAIR: {SupervisorPhase.RETRY, SupervisorPhase.FAILED},
    SupervisorPhase.RETRY: {SupervisorPhase.EXECUTE, SupervisorPhase.FAILED},
    SupervisorPhase.DELIVER: {SupervisorPhase.COMPLETED, SupervisorPhase.FAILED},
    SupervisorPhase.BLOCKED: set(),
    SupervisorPhase.COMPLETED: set(),
    SupervisorPhase.FAILED: set(),
}


@dataclass(frozen=True)
class SupervisorResult:
    task_id: str
    status: TaskStatus
    allowed: bool
    attempts: int
    output: Any = None
    error: str | None = None


class Supervisor:
    """Evidence-driven supervisor with a durable discover-to-deliver lifecycle."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain, permissions: PermissionBoundary, authority: AuthorityApprovalLedger | None = None) -> None:
        self.state, self.audit, self.permissions, self.authority = state, audit, permissions, authority
        self.recovery = RecoveryRunner(state, audit)
        self.lease = TaskLease(state, audit)
        self.owner = f"supervisor:{uuid.uuid4().hex}"

    def _phase(self, task_id: str) -> SupervisorPhase:
        record = self.state.get(f"supervisor:{task_id}") or {}
        return SupervisorPhase(record.get("phase", SupervisorPhase.DISCOVER.value))

    def _set_phase(self, task_id: str, target: SupervisorPhase, **details: Any) -> None:
        key = f"supervisor:{task_id}"
        record = self.state.get(key) or {"task_id": task_id}
        current = SupervisorPhase(record.get("phase", SupervisorPhase.DISCOVER.value))
        if target not in _PHASE_ORDER[current] and target is not current:
            raise RuntimeError(f"invalid supervisor phase: {current.value} -> {target.value}")
        self.state.set(key, {**record, "phase": target.value, "phase_details": details})
        self.audit.record("supervisor.phase", {"task_id": task_id, "from": current.value, "to": target.value, "details": details})

    def register(self, task_id: str, action: str, risk: ActionRisk, handler: Callable[[], Any], *, max_attempts: int = 3, retryable: Callable[[Exception], bool] | None = None) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.state.set(f"supervisor:{task_id}", {
            "task_id": task_id, "action": action, "risk": risk.value,
            "status": TaskStatus.PENDING.value, "phase": SupervisorPhase.DISCOVER.value,
            "max_attempts": max_attempts,
        })
        setattr(self, f"_handler_{task_id}", (handler, retryable))
        self.audit.record("task.registered", {"task_id": task_id, "action": action, "risk": risk.value})

    def run(self, task_id: str, *, lease_ttl_seconds: float = 60.0) -> SupervisorResult:
        record = self.state.get(f"supervisor:{task_id}")
        if record is None:
            return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error="task is not registered")
        requested_risk = ActionRisk(record["risk"])
        decision = self.permissions.decide(record["action"], requested_risk)
        if requested_risk is ActionRisk.IRREVERSIBLE:
            if self.authority is None:
                return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error="explicit authority required")
            approval = self.authority.check(task_id, record["action"], requested_risk)
            decision = self.permissions.decide(record["action"], requested_risk, explicit_approval=approval.approved)
            if not decision.allowed or not approval.approved:
                self._set_phase(task_id, SupervisorPhase.BLOCKED, reason="authority_or_permission_denied")
                return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=decision.reason)
        if not decision.allowed:
            self._set_phase(task_id, SupervisorPhase.BLOCKED, reason=decision.reason)
            return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=decision.reason)

        lease = self.lease.acquire(task_id, self.owner, ttl_seconds=lease_ttl_seconds)
        if not lease.acquired:
            self._set_phase(task_id, SupervisorPhase.BLOCKED, reason="task lease unavailable")
            return SupervisorResult(task_id, TaskStatus.FAILED, True, 0, error="task lease unavailable")

        try:
            if requested_risk is ActionRisk.IRREVERSIBLE:
                consumed = self.authority.consume(task_id, record["action"], requested_risk)
                if not consumed.approved:
                    self._set_phase(task_id, SupervisorPhase.BLOCKED, reason=consumed.reason)
                    return SupervisorResult(task_id, TaskStatus.FAILED, False, 0, error=consumed.reason)
            self._set_phase(task_id, SupervisorPhase.PLAN)
            self._set_phase(task_id, SupervisorPhase.SELECT)
            self._set_phase(task_id, SupervisorPhase.EXECUTE)
            handler, retryable = getattr(self, f"_handler_{task_id}", (None, None))
            if handler is None:
                self._set_phase(task_id, SupervisorPhase.FAILED, reason="execution handler is unavailable")
                return SupervisorResult(task_id, TaskStatus.FAILED, True, 0, error="execution handler is unavailable")
            self.state.set(f"supervisor:{task_id}", {**self.state.get(f"supervisor:{task_id}"), "status": TaskStatus.RUNNING.value})
            lease_lost = threading.Event()
            stop = threading.Event()
            interval = max(0.01, min(1.0, lease_ttl_seconds / 4.0))
            def heartbeat() -> None:
                while not stop.wait(interval):
                    if not self.lease.heartbeat(task_id, self.owner, ttl_seconds=lease_ttl_seconds).acquired:
                        lease_lost.set()
                        return
            thread = threading.Thread(target=heartbeat, daemon=True)
            thread.start()
            try:
                result = self.recovery.run(task_id, handler, max_attempts=int(record["max_attempts"]), retryable=retryable)
            finally:
                stop.set()
                thread.join(timeout=max(1.0, interval * 2))
            if lease_lost.is_set() or not self.lease.is_owned(task_id, self.owner):
                self.audit.record("task.lease_lost", {"task_id": task_id, "owner": self.owner})
                self._set_phase(task_id, SupervisorPhase.FAILED, reason="execution lease lost")
                return SupervisorResult(task_id, TaskStatus.FAILED, True, result.attempts, error="execution lease lost")
            self._set_phase(task_id, SupervisorPhase.VERIFY, status=result.status.value)
            if result.status is TaskStatus.SUCCESS:
                self._set_phase(task_id, SupervisorPhase.DELIVER)
                self._set_phase(task_id, SupervisorPhase.COMPLETED)
                final_status = TaskStatus.SUCCESS
            else:
                self._set_phase(task_id, SupervisorPhase.REPAIR, error=result.error)
                self._set_phase(task_id, SupervisorPhase.RETRY if result.attempts < int(record["max_attempts"]) else SupervisorPhase.FAILED)
                final_status = result.status
            final = self.state.get(f"supervisor:{task_id}") or record
            self.state.set(f"supervisor:{task_id}", {**final, "status": final_status.value, "error": result.error})
            return SupervisorResult(task_id, final_status, True, result.attempts, output=result.output, error=result.error)
        finally:
            self.lease.release(task_id, self.owner)


__all__ = ["Supervisor", "SupervisorResult", "SupervisorPhase"]

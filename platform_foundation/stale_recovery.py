from __future__ import annotations

import time
from dataclasses import dataclass

from .audit_chain import AuditChain
from .lease import TaskLease
from .persistent_state import SQLiteStateStore
from .task_state import TaskStatus


@dataclass(frozen=True)
class RecoveredTask:
    task_id: str
    previous_status: str
    status: str
    reason: str


class StaleTaskRecovery:
    """Reconcile durable RUNNING tasks whose execution lease has expired."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain) -> None:
        self.state = state
        self.audit = audit
        self.lease = TaskLease(state, audit)

    def recover_expired(self, task_ids: list[str] | None = None, *, now: float | None = None) -> list[RecoveredTask]:
        now = time.time() if now is None else now
        if task_ids is None:
            task_ids = self._discover_task_ids()
        recovered: list[RecoveredTask] = []
        for task_id in task_ids:
            record = self.state.get(f"supervisor:{task_id}")
            if not record or record.get("status") != TaskStatus.RUNNING.value:
                continue
            lease = self.state.get(f"lease:{task_id}")
            if lease and lease.get("owner") and float(lease.get("expires_at", 0)) > now:
                continue
            updated = {
                **record,
                "status": TaskStatus.RETRYING.value,
                "recovery_reason": "execution lease expired or missing",
                "recovered_at": now,
            }
            self.state.set(f"supervisor:{task_id}", updated)
            self.audit.record("task.stale_recovered", {
                "task_id": task_id,
                "previous_status": TaskStatus.RUNNING.value,
                "status": TaskStatus.RETRYING.value,
                "reason": "execution lease expired or missing",
            })
            recovered.append(RecoveredTask(task_id, TaskStatus.RUNNING.value, TaskStatus.RETRYING.value, "execution lease expired or missing"))
        return recovered

    def _discover_task_ids(self) -> list[str]:
        snapshot = self.state.snapshot()
        prefix = "supervisor:"
        return sorted(
            key[len(prefix):]
            for key, value in snapshot.items()
            if key.startswith(prefix) and isinstance(value, dict) and value.get("task_id")
        )


__all__ = ["RecoveredTask", "StaleTaskRecovery"]

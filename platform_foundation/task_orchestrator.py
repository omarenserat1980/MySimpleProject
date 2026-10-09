from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .persistent_state import SQLiteStateStore
from .task_state import TaskStatus, transition


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    status: TaskStatus
    attempts: int
    error: str | None = None
    output: Any = None


class TaskOrchestrator:
    """Durable task lifecycle with validated state transitions."""

    def __init__(self, store: SQLiteStateStore) -> None:
        self.store = store

    def current(self, task_id: str) -> TaskRecord:
        value = self.store.get(f"task:{task_id}")
        if value is None:
            return TaskRecord(task_id, TaskStatus.PENDING, 0)
        return TaskRecord(
            task_id,
            TaskStatus(value["status"]),
            int(value.get("attempts", 0)),
            value.get("error"),
            value.get("output"),
        )

    def _save(self, record: TaskRecord) -> TaskRecord:
        self.store.set(f"task:{record.task_id}", {
            "task_id": record.task_id,
            "status": record.status.value,
            "attempts": record.attempts,
            "error": record.error,
            "output": record.output,
        })
        return record

    def transition(self, task_id: str, target: TaskStatus, **fields: Any) -> TaskRecord:
        current = self.current(task_id)
        next_status = transition(current.status, target)
        return self._save(TaskRecord(
            task_id,
            next_status,
            int(fields.get("attempts", current.attempts)),
            fields.get("error", current.error),
            fields.get("output", current.output),
        ))

    def start(self, task_id: str) -> TaskRecord:
        return self.transition(task_id, TaskStatus.RUNNING)

    def retry(self, task_id: str, error: str) -> TaskRecord:
        current = self.current(task_id)
        attempts = current.attempts + 1
        target = TaskStatus.RETRYING if current.status in {TaskStatus.RUNNING, TaskStatus.FAILED} else TaskStatus.RETRYING
        return self.transition(task_id, target, attempts=attempts, error=error)

    def succeed(self, task_id: str, output: Any = None) -> TaskRecord:
        return self.transition(task_id, TaskStatus.SUCCESS, output=output, error=None)

    def fail(self, task_id: str, error: str) -> TaskRecord:
        return self.transition(task_id, TaskStatus.FAILED, error=error)

    def cancel(self, task_id: str) -> TaskRecord:
        return self.transition(task_id, TaskStatus.CANCELLED)

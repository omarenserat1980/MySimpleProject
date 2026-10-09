from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from .audit_chain import AuditChain
from .persistent_state import SQLiteStateStore
from .task_state import TaskStatus

T = TypeVar("T")


@dataclass(frozen=True)
class ResumeResult:
    task_id: str
    status: TaskStatus
    resumed: bool
    checkpoint: object | None
    output: T | None = None
    error: str | None = None


class ResumeSupervisor:
    """Resume a task from durable checkpoint state without losing evidence."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain) -> None:
        self.state = state
        self.audit = audit

    def checkpoint(self, task_id: str, value: object) -> None:
        if not task_id:
            raise ValueError("task_id is required")
        self.state.set(
            f"checkpoint:{task_id}",
            {"task_id": task_id, "value": value},
        )
        self.audit.record(
            "task.checkpoint",
            {"task_id": task_id},
        )

    def load_checkpoint(self, task_id: str) -> object | None:
        item = self.state.get(f"checkpoint:{task_id}")
        return None if item is None else item.get("value")

    def run(
        self,
        task_id: str,
        handler: Callable[[object | None], T],
    ) -> ResumeResult:
        checkpoint = self.load_checkpoint(task_id)
        resumed = checkpoint is not None
        self.audit.record(
            "task.resume" if resumed else "task.start",
            {"task_id": task_id, "resumed": resumed},
        )

        try:
            output = handler(checkpoint)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            self.state.set(
                f"resume:{task_id}",
                {"task_id": task_id, "status": TaskStatus.FAILED.value, "error": error},
            )
            self.audit.record(
                "task.resume_failed",
                {"task_id": task_id, "error": error},
            )
            return ResumeResult(
                task_id,
                TaskStatus.FAILED,
                resumed,
                checkpoint,
                error=error,
            )

        self.state.set(
            f"resume:{task_id}",
            {"task_id": task_id, "status": TaskStatus.SUCCESS.value},
        )
        self.audit.record(
            "task.resume_success",
            {"task_id": task_id, "resumed": resumed},
        )
        return ResumeResult(
            task_id,
            TaskStatus.SUCCESS,
            resumed,
            checkpoint,
            output=output,
        )


__all__ = ["ResumeResult", "ResumeSupervisor"]

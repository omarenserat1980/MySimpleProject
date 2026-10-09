from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from .audit_chain import AuditChain
from .persistent_state import SQLiteStateStore
from .task_state import TaskStatus, transition

T = TypeVar("T")


@dataclass(frozen=True)
class RecoveryResult:
    task_id: str
    status: TaskStatus
    attempts: int
    output: object | None = None
    error: str | None = None


class RecoveryRunner:
    """Run a task with durable checkpoints and bounded retry behavior."""

    def __init__(self, state: SQLiteStateStore, audit: AuditChain) -> None:
        self.state = state
        self.audit = audit

    def run(
        self,
        task_id: str,
        handler: Callable[[], T],
        *,
        max_attempts: int = 3,
        retryable: Callable[[Exception], bool] | None = None,
    ) -> RecoveryResult:
        if not task_id:
            raise ValueError("task_id is required")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        retryable = retryable or (lambda _error: True)
        key = f"recovery:{task_id}"
        previous = self.state.get(key, {})
        attempts = int(previous.get("attempts", 0))

        while attempts < max_attempts:
            attempts += 1
            self.state.set(
                key,
                {
                    "task_id": task_id,
                    "status": TaskStatus.RUNNING.value,
                    "attempts": attempts,
                    "last_error": None,
                },
            )
            self.audit.record(
                "task.attempt",
                {"task_id": task_id, "attempt": attempts},
            )

            try:
                output = handler()
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                if retryable(exc) and attempts < max_attempts:
                    self.state.set(
                        key,
                        {
                            "task_id": task_id,
                            "status": TaskStatus.RETRYING.value,
                            "attempts": attempts,
                            "last_error": error,
                        },
                    )
                    self.audit.record(
                        "task.retry",
                        {"task_id": task_id, "attempt": attempts, "error": error},
                    )
                    continue

                self.state.set(
                    key,
                    {
                        "task_id": task_id,
                        "status": TaskStatus.FAILED.value,
                        "attempts": attempts,
                        "last_error": error,
                    },
                )
                self.audit.record(
                    "task.failed",
                    {"task_id": task_id, "attempts": attempts, "error": error},
                )
                return RecoveryResult(
                    task_id, TaskStatus.FAILED, attempts, error=error
                )

            self.state.set(
                key,
                {
                    "task_id": task_id,
                    "status": TaskStatus.SUCCESS.value,
                    "attempts": attempts,
                    "last_error": None,
                },
            )
            self.audit.record(
                "task.success",
                {"task_id": task_id, "attempts": attempts},
            )
            return RecoveryResult(
                task_id, TaskStatus.SUCCESS, attempts, output=output
            )

        # Defensive guard: the loop always returns before reaching this point.
        raise RuntimeError("recovery loop exhausted unexpectedly")


__all__ = ["RecoveryResult", "RecoveryRunner"]

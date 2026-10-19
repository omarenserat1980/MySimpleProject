"""Opt-in adapter for recording truthful Brain task outcomes in SQLite."""
from __future__ import annotations

import uuid
from typing import Any, Callable, TypeVar

from .sqlite_evidence_store import ExperimentMemory

T = TypeVar("T")


class TaskEvidenceRunner:
    """Record STARTED and terminal outcomes; never persist exception text/results."""

    def __init__(self, memory: ExperimentMemory | None = None):
        self.memory = memory or ExperimentMemory()
        self.memory.init()

    def recent(self, subject: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return previous events for a planner to avoid repeating completed work."""
        return self.memory.list_events(subject=subject, limit=limit)

    def run(
        self,
        task: Callable[[], T],
        *,
        project: str,
        subject: str,
        task_name: str,
        environment: dict[str, Any] | None = None,
        evidence: list[Any] | None = None,
        limitations: list[Any] | None = None,
    ) -> T:
        run_id = str(uuid.uuid4())
        common = {
            "project": project,
            "subject": subject,
            "event_type": "brain_task",
            "environment": environment or {},
            "evidence": evidence or [],
            "limitations": limitations or [
                "Records only the wrapped software task outcome.",
                "Does not prove physical hardware execution, mining, or revenue.",
            ],
        }
        self.memory.record({
            **common, "event_id": f"{run_id}:started", "status": "STARTED",
            "measurements": {"task_name": task_name, "run_id": run_id},
        })
        try:
            result = task()
        except Exception as exc:
            self.memory.record({
                **common, "event_id": f"{run_id}:failed", "status": "FAILED",
                "measurements": {
                    "task_name": task_name, "run_id": run_id,
                    "exception_type": type(exc).__name__,
                },
            })
            raise
        self.memory.record({
            **common, "event_id": f"{run_id}:succeeded", "status": "SUCCEEDED",
            "measurements": {"task_name": task_name, "run_id": run_id},
        })
        return result

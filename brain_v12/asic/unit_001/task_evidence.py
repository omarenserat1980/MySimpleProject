"""Task execution adapter that records truthful outcomes in ExperimentMemory.

This is an opt-in wrapper, not a claim that every Brain execution path uses it.
It records STARTED before invoking a task, then SUCCEEDED or FAILED afterwards.
Exception messages and task return values are deliberately not persisted.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, TypeVar
import uuid

from .sqlite_evidence_store import ExperimentMemory

T = TypeVar("T")


class TaskEvidenceRunner:
    def __init__(self, memory: ExperimentMemory | None = None):
        self.memory = memory or ExperimentMemory()

    def recent(self, subject: str, limit: int = 20) -> list[dict[str, Any]]:
        """Return previous evidence for planning; newest events first."""
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
        """Run one callable and persist STARTED plus its final truthful status."""
        run_id = str(uuid.uuid4())
        common = {
            "project": project,
            "subject": subject,
            "environment": environment or {},
            "evidence": evidence or [],
            "limitations": limitations or [
                "This event proves only the outcome of this wrapped software task.",
                "It does not prove physical hardware execution unless evidence explicitly establishes that.",
            ],
        }
        self.memory.record({
            **common,
            "event_id": f"{run_id}:started",
            "event_type": "brain_task",
            "status": "STARTED",
            "measurements": {"task_name": task_name, "run_id": run_id},
        })
        try:
            result = task()
        except Exception as exc:
            self.memory.record({
                **common,
                "event_id": f"{run_id}:failed",
                "event_type": "brain_task",
                "status": "FAILED",
                "measurements": {
                    "task_name": task_name,
                    "run_id": run_id,
                    "exception_type": type(exc).__name__,
                },
            })
            raise
        self.memory.record({
            **common,
            "event_id": f"{run_id}:succeeded",
            "event_type": "brain_task",
            "status": "SUCCEEDED",
            "measurements": {"task_name": task_name, "run_id": run_id},
        })
        return result

from __future__ import annotations

from pathlib import Path

from ..audit import AuditLog
from .. import service
from ..workflows import get_run
from .worker import execute_queued_run


class NativeOrchestrator:
    """Single-run orchestration boundary for Brain-native CI."""

    def __init__(self, root: Path | None = None):
        self.root = root or service.ROOT
        self.audit = AuditLog(self.root)

    def execute(self, run_id: int) -> dict:
        run = get_run(run_id)
        self.audit.record("brain-runner", "workflow.start", f"{run['namespace']}/{run['repository']}#{run_id}")
        try:
            result = execute_queued_run(run_id)
            self.audit.record(
                "brain-runner",
                "workflow.complete",
                f"{run['namespace']}/{run['repository']}#{run_id}",
                "success" if result["status"] == "success" else "failed",
                {"status": result["status"]},
            )
            return result
        except Exception as exc:
            self.audit.record(
                "brain-runner",
                "workflow.complete",
                f"{run['namespace']}/{run['repository']}#{run_id}",
                "failed",
                {"error": str(exc)},
            )
            raise

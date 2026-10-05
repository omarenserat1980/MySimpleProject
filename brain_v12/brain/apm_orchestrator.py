"""Resumable APM orchestrator driven by the unified build report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Any

from .apm_build_report import build_report


@dataclass
class APMCheckpoint:
    run_id: str
    status: str
    next_action: str
    current_stage: str | None
    completed: list[str]
    failed: list[str]
    blocked: list[str]
    cached: list[str]
    updated_at: float

    def save(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "APMCheckpoint":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


class APMOrchestrator:
    def __init__(self, state_path: str):
        self.state_path = state_path

    def decide(
        self,
        *,
        run_id: str,
        runner_status: str,
        current_stage: str | None,
        completed: list[str],
        failed: list[str],
        blocked: list[str],
        cached: list[str],
    ) -> APMCheckpoint:
        report = build_report(
            completed=len(completed),
            blocked=len(blocked),
            cached=len(cached),
            failed=len(failed),
            runner_status=runner_status,
        )
        checkpoint = APMCheckpoint(
            run_id=run_id,
            status=report.status,
            next_action=report.next_action,
            current_stage=current_stage,
            completed=list(completed),
            failed=list(failed),
            blocked=list(blocked),
            cached=list(cached),
            updated_at=time.time(),
        )
        checkpoint.save(self.state_path)
        return checkpoint

    def resume(self) -> dict[str, Any]:
        checkpoint = APMCheckpoint.load(self.state_path)
        return {
            "run_id": checkpoint.run_id,
            "status": checkpoint.status,
            "next_action": checkpoint.next_action,
            "current_stage": checkpoint.current_stage,
            "resume_units": checkpoint.failed or checkpoint.blocked,
            "skip_units": checkpoint.completed + checkpoint.cached,
        }

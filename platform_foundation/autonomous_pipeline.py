from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .apm import APM
from .stage_orchestrator import StageOrchestrator, StageState


@dataclass(frozen=True)
class PipelineResult:
    stage_before: int
    stage_after: int
    status: str
    attempts: int
    verified: bool


@dataclass(frozen=True)
class PipelineRun:
    start_stage: int
    end_stage: int
    stages_completed: int
    stopped_stage: int | None
    status: str


class AutonomousPipeline:
    """APM-instrumented, resumable driver for the durable 41-stage pipeline."""

    def __init__(self, orchestrator: StageOrchestrator, apm: APM) -> None:
        self.orchestrator = orchestrator
        self.apm = apm

    def run_stage(
        self, *, execute: Callable[[StageState], Any],
        verify: Callable[[StageState, Any], bool], max_attempts: int = 3,
        task_id: str | None = None, run_id: str | None = None,
        commit_sha: str | None = None,
    ) -> PipelineResult:
        before = self.orchestrator.current()
        attempts = 0
        verified = False

        def measured_execute(state: StageState) -> Any:
            nonlocal attempts
            attempts += 1
            with self.apm.operation(
                f"stage.{state.stage}.execute",
                task_id=task_id, run_id=run_id, commit_sha=commit_sha,
            ) as telemetry:
                telemetry["retries"] = max(0, attempts - 1)
                return execute(state)

        def measured_verify(state: StageState, result: Any) -> bool:
            nonlocal verified
            with self.apm.operation(
                f"stage.{state.stage}.verify",
                task_id=task_id, run_id=run_id, commit_sha=commit_sha,
            ):
                verified = bool(verify(state, result))
                return verified

        try:
            after = self.orchestrator.run_next(
                execute=measured_execute, verify=measured_verify,
                max_attempts=max_attempts,
            )
            self.apm.counter(
                "pipeline.stages.completed", 1,
                task_id=task_id, run_id=run_id, commit_sha=commit_sha,
                dimensions={"stage": str(before.stage)},
            )
            return PipelineResult(before.stage, after.stage, after.status, attempts, verified)
        except Exception:
            self.apm.counter(
                "pipeline.stages.failed", 1,
                task_id=task_id, run_id=run_id, commit_sha=commit_sha,
                dimensions={"stage": str(before.stage)},
            )
            raise

    def run_until(
        self, *,
        execute: Callable[[StageState], Any],
        verify: Callable[[StageState, Any], bool],
        stop_stage: int | None = None,
        max_attempts: int = 3,
        task_id: str | None = None,
        run_id: str | None = None,
        commit_sha: str | None = None,
    ) -> PipelineRun:
        """Continue from the durable checkpoint until a gate fails or target is reached."""
        if stop_stage is not None and not 1 <= stop_stage <= self.orchestrator.TOTAL_STAGES:
            raise ValueError("stop_stage must be between 1 and 41")
        start = self.orchestrator.current().stage
        target = stop_stage or self.orchestrator.TOTAL_STAGES
        completed = 0

        while self.orchestrator.current().stage <= target:
            current = self.orchestrator.current()
            if current.status == "FAILED":
                return PipelineRun(start, current.stage, completed, current.stage, "BLOCKED")
            result = self.run_stage(
                execute=execute, verify=verify, max_attempts=max_attempts,
                task_id=task_id, run_id=run_id, commit_sha=commit_sha,
            )
            completed += 1
            if result.stage_before == target:
                return PipelineRun(start, result.stage_after, completed, None, result.status)
        return PipelineRun(start, self.orchestrator.current().stage, completed, None, "COMPLETE")

    def progress(self) -> dict[str, Any]:
        state = self.orchestrator.current()
        return {
            "stage": state.stage, "total_stages": self.orchestrator.TOTAL_STAGES,
            "completed_stages": max(0, state.stage - 1),
            "progress_percent": round((state.stage - 1) / self.orchestrator.TOTAL_STAGES * 100, 2),
            "status": state.status, "attempts": state.attempts,
            "last_error": state.last_error, "apm": self.apm.summary(),
        }


__all__ = ["AutonomousPipeline", "PipelineResult", "PipelineRun"]

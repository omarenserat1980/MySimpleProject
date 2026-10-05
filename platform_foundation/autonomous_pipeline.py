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


class AutonomousPipeline:
    """APM-instrumented driver for the durable 41-stage orchestrator.

    It coordinates execution and telemetry but never bypasses StageOrchestrator
    gates, authority checks, or independent verification.
    """

    def __init__(self, orchestrator: StageOrchestrator, apm: APM) -> None:
        self.orchestrator = orchestrator
        self.apm = apm

    def run_stage(
        self,
        *,
        execute: Callable[[StageState], Any],
        verify: Callable[[StageState, Any], bool],
        max_attempts: int = 3,
        task_id: str | None = None,
        run_id: str | None = None,
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
            ) as telemetry:
                verified = bool(verify(state, result))
                return verified

        try:
            after = self.orchestrator.run_next(
                execute=measured_execute,
                verify=measured_verify,
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

    def progress(self) -> dict[str, Any]:
        state = self.orchestrator.current()
        return {
            "stage": state.stage,
            "total_stages": self.orchestrator.TOTAL_STAGES,
            "completed_stages": max(0, state.stage - 1),
            "progress_percent": round((state.stage - 1) / self.orchestrator.TOTAL_STAGES * 100, 2),
            "status": state.status,
            "attempts": state.attempts,
            "last_error": state.last_error,
            "apm": self.apm.summary(),
        }


__all__ = ["AutonomousPipeline", "PipelineResult"]

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable
import time

from .apm import APM
from .parallel_chunks import ParallelChunkRunner, ChunkResult
from .stage_orchestrator import StageOrchestrator, StageState
from .brain_ci_executor import BrainCIExecutor


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
    run_id: str | None = None


class AutonomousPipeline:
    """Durable 41-stage driver with optional dependency-aware chunk parallelism."""

    RUN_KEY = "brain.autonomous_pipeline.last_run"
    CHECKPOINT_KEY = "brain.autonomous_pipeline.verified_checkpoint"

    def __init__(
        self,
        orchestrator: StageOrchestrator,
        apm: APM,
        chunk_runner: ParallelChunkRunner | None = None,
        ci_executor: BrainCIExecutor | None = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.apm = apm
        self.chunk_runner = chunk_runner
        self.ci_executor = ci_executor

    def _save_run(self, run: PipelineRun) -> None:
        self.orchestrator.store.set(self.RUN_KEY, asdict(run))

    def checkpoint(self) -> dict[str, Any] | None:
        return self.orchestrator.store.get(self.CHECKPOINT_KEY)

    def _save_checkpoint(self, *, state: StageState, run_id: str | None) -> None:
        self.orchestrator.store.set(
            self.CHECKPOINT_KEY,
            {"stage": state.stage, "step": state.step, "revision": state.revision,
             "status": state.status, "run_id": run_id},
        )

    def last_run(self) -> PipelineRun | None:
        value = self.orchestrator.store.get(self.RUN_KEY)
        return PipelineRun(**value) if value else None

    def run_parallel_stage(
        self,
        *,
        chunks: list[str],
        execute_chunk: Callable[[str, dict[str, Any]], Any],
        verify_chunk: Callable[[str, Any], bool],
        dependencies: dict[str, list[str]] | None = None,
        max_workers: int = 4,
        max_attempts: int = 1,
        task_id: str | None = None,
        run_id: str | None = None,
        commit_sha: str | None = None,
    ) -> list[ChunkResult]:
        """Run independent work inside the current stage, then gate the stage."""
        if self.chunk_runner is None:
            raise RuntimeError("parallel chunk runner is not configured")
        before = self.orchestrator.current()
        effective_run_id = run_id or f"pipeline-{time.time_ns()}"
        attempts = 0
        last: list[ChunkResult] = []

        while attempts < max_attempts:
            attempts += 1
            last = self.chunk_runner.run(
                f"{effective_run_id}:stage-{before.stage}",
                chunks,
                execute_chunk,
                verify_chunk,
                dependencies=dependencies,
                max_workers=max_workers,
            )
            if all(item.status == "SUCCESS" for item in last):
                # The stage gate opens only after every required chunk is independently verified.
                after = self.orchestrator.advance(
                    stage=before.stage + 1 if before.stage < self.orchestrator.TOTAL_STAGES else before.stage,
                    step=1,
                    gate_passed=True,
                )
                self._save_checkpoint(state=after, run_id=effective_run_id)
                self.apm.counter(
                    "pipeline.parallel_stages.completed", 1,
                    task_id=task_id, run_id=effective_run_id, commit_sha=commit_sha,
                    dimensions={"stage": str(before.stage), "chunks": str(len(chunks))},
                )
                return last

        self.apm.counter(
            "pipeline.parallel_stages.failed", 1,
            task_id=task_id, run_id=effective_run_id, commit_sha=commit_sha,
            dimensions={"stage": str(before.stage)},
        )
        raise RuntimeError(
            f"stage {before.stage} parallel gate failed after {attempts} attempt(s)"
        )

    def run_stage(
        self, *, execute: Callable[[StageState], Any],
        verify: Callable[[StageState, Any], bool], max_attempts: int = 3,
        task_id: str | None = None, run_id: str | None = None,
        commit_sha: str | None = None,
    ) -> PipelineResult:
        before = self.orchestrator.current()
        attempts = 0

        def measured_execute(state: StageState) -> Any:
            nonlocal attempts
            attempts += 1
            with self.apm.operation(f"stage.{state.stage}.execute",
                                   task_id=task_id, run_id=run_id, commit_sha=commit_sha) as telemetry:
                telemetry["retries"] = max(0, attempts - 1)
                return execute(state)

        def measured_verify(state: StageState, result: Any) -> bool:
            with self.apm.operation(f"stage.{state.stage}.verify",
                                   task_id=task_id, run_id=run_id, commit_sha=commit_sha):
                return bool(verify(state, result))

        try:
            after = self.orchestrator.run_next(
                execute=measured_execute, verify=measured_verify, max_attempts=max_attempts,
            )
            self.apm.counter("pipeline.stages.completed", 1, task_id=task_id,
                             run_id=run_id, commit_sha=commit_sha,
                             dimensions={"stage": str(before.stage)})
            self._save_checkpoint(state=after, run_id=run_id)
            return PipelineResult(before.stage, after.stage, after.status, attempts, True)
        except Exception:
            self.apm.counter("pipeline.stages.failed", 1, task_id=task_id,
                             run_id=run_id, commit_sha=commit_sha,
                             dimensions={"stage": str(before.stage)})
            raise

    def run_until(
        self, *, execute: Callable[[StageState], Any],
        verify: Callable[[StageState, Any], bool],
        stop_stage: int | None = None, max_attempts: int = 3,
        task_id: str | None = None, run_id: str | None = None,
        commit_sha: str | None = None,
    ) -> PipelineRun:
        if stop_stage is not None and not 1 <= stop_stage <= self.orchestrator.TOTAL_STAGES:
            raise ValueError("stop_stage must be between 1 and 41")
        start = self.orchestrator.current().stage
        target = stop_stage or self.orchestrator.TOTAL_STAGES
        completed = 0
        effective_run_id = run_id or f"pipeline-{time.time_ns()}"
        execution = self.execution_health()
        if not execution["healthy"]:
            blocked = PipelineRun(
                start, self.orchestrator.current().stage, 0,
                self.orchestrator.current().stage, "BLOCKED", effective_run_id
            )
            self._save_run(blocked)
            self.apm.counter("pipeline.runs.blocked", 1, task_id=task_id,
                             run_id=effective_run_id, commit_sha=commit_sha)
            return blocked
        self.apm.counter("pipeline.runs.started", 1, task_id=task_id,
                         run_id=effective_run_id, commit_sha=commit_sha)
        try:
            while self.orchestrator.current().stage <= target:
                current = self.orchestrator.current()
                if current.status == "FAILED":
                    result = PipelineRun(start, current.stage, completed, current.stage, "BLOCKED", effective_run_id)
                    self._save_run(result)
                    return result
                result = self.run_stage(
                    execute=execute, verify=verify, max_attempts=max_attempts,
                    task_id=task_id, run_id=effective_run_id, commit_sha=commit_sha,
                )
                completed += 1
                if result.stage_before == target:
                    final = PipelineRun(start, result.stage_after, completed, None, result.status, effective_run_id)
                    self._save_run(final)
                    self.apm.counter("pipeline.runs.completed", 1, task_id=task_id,
                                     run_id=effective_run_id, commit_sha=commit_sha)
                    return final
            final = PipelineRun(start, self.orchestrator.current().stage, completed, None, "COMPLETE", effective_run_id)
            self._save_run(final)
            return final
        except Exception:
            failed = PipelineRun(start, self.orchestrator.current().stage, completed,
                                 self.orchestrator.current().stage, "FAILED", effective_run_id)
            self._save_run(failed)
            self.apm.counter("pipeline.runs.failed", 1, task_id=task_id,
                             run_id=effective_run_id, commit_sha=commit_sha)
            raise

    def execution_health(self) -> dict[str, Any]:
        if self.ci_executor is None:
            return {"healthy": False, "status": "BLOCKED", "reason": "brain_ci_executor_not_configured"}
        readiness = self.ci_executor.readiness()
        health = self.ci_executor.health()
        if not readiness["ready"] or not health["healthy"]:
            return {"healthy": False, "status": "BLOCKED", "reason": "brain_ci_executor_unavailable",
                    "readiness": readiness, "executor": health}
        return {"healthy": True, "status": "READY", "readiness": readiness, "executor": health}

    def health(self) -> dict[str, Any]:
        state = self.orchestrator.current()
        checkpoint = self.checkpoint()
        issues = []
        if state.status == "FAILED":
            issues.append("stage_failed")
        if checkpoint and int(checkpoint["stage"]) != state.stage:
            issues.append("checkpoint_mismatch")
        if checkpoint is None and state.stage > 1:
            issues.append("missing_checkpoint")
        execution = self.execution_health()
        if not execution["healthy"]:
            issues.append("brain_ci_executor_unavailable")
        return {"healthy": not issues, "stage": state.stage, "status": state.status, "issues": issues, "checkpoint": checkpoint, "execution": execution}

    def progress(self) -> dict[str, Any]:
        state = self.orchestrator.current()
        return {
            "stage": state.stage, "total_stages": self.orchestrator.TOTAL_STAGES,
            "completed_stages": max(0, state.stage - 1),
            "progress_percent": round((state.stage - 1) / self.orchestrator.TOTAL_STAGES * 100, 2),
            "status": state.status, "attempts": state.attempts,
            "last_error": state.last_error, "last_run": self.last_run(),
            "apm": self.apm.summary(),
        }


__all__ = ["AutonomousPipeline", "PipelineResult", "PipelineRun"]

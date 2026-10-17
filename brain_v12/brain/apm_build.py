"""APM BUILD integration with Brain's evidence-first execution coordinator."""

from __future__ import annotations

from typing import Any, Callable

from .execution_coordinator import BrainExecutionCoordinator
from .parallel_stage_scheduler import (
    APMBuildOrchestrator,
    ParallelStageScheduler,
    Stage,
)

StageExecutor = Callable[[Stage], dict[str, Any]]
StageVerifier = Callable[[Stage, dict[str, Any]], dict[str, Any] | bool]
FinalGate = Callable[[dict[str, Any]], dict[str, Any] | bool]


class BrainAPMBuild:
    """Run a dependency graph through Brain's existing execution authority."""

    def __init__(
        self,
        coordinator: BrainExecutionCoordinator | None = None,
        max_workers: int = 4,
        retry_limit: int = 1,
    ) -> None:
        self.coordinator = coordinator or BrainExecutionCoordinator()
        self.max_workers = max_workers
        self.retry_limit = retry_limit

    def run(
        self,
        stages: list[Stage],
        state_dir: str,
        executor: StageExecutor,
        verifier: StageVerifier,
        final_gate: FinalGate | None = None,
    ) -> dict[str, Any]:
        scheduler = ParallelStageScheduler(
            stages,
            state_dir,
            max_workers=self.max_workers,
            retry_limit=self.retry_limit,
        )
        apm = APMBuildOrchestrator(scheduler)

        def coordinated_executor(stage: Stage) -> dict[str, Any]:
            control = self.coordinator.create(
                stage.metadata.get("objective", stage.id),
                max_attempts=1,
            )
            control_id = control["control"]["id"]

            result = self.coordinator.execute(
                control_id,
                lambda _objective: executor(stage),
                lambda raw: verifier(stage, raw),
            )
            result["apm_control_task_id"] = control_id
            return result

        def coordinated_verifier(
            stage: Stage, result: dict[str, Any]
        ) -> dict[str, Any]:
            if result.get("status") == "VERIFIED_COMPLETED":
                control = result.get("control", {})
                evidence = result.get("task", {})
                evidence_ref = (
                    result.get("evidence_ref")
                    or control.get("evidence_ref")
                    or evidence.get("evidence_ref")
                )
                return {
                    "verified": bool(evidence_ref),
                    "evidence_ref": evidence_ref
                    or f"apm://{stage.id}/coordinator-verified",
                    "control_task_id": result.get("apm_control_task_id"),
                }
            return {
                "verified": False,
                "reason": result.get("error", "COORDINATOR_NOT_VERIFIED"),
                "control_task_id": result.get("apm_control_task_id"),
            }

        return apm.run(
            coordinated_executor,
            coordinated_verifier,
            final_gate=final_gate,
        )

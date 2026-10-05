"""APM executor for the existing cinematic MediaProductionPipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .apm_media_adapter import stages_from_media_pipeline
from .parallel_stage_scheduler import ParallelStageScheduler


class APMMediaExecutor:
    """Execute media stages independently while preserving quality gates."""

    def __init__(self, media_pipeline: Any, *, state_dir: str, max_workers: int = 2,
                 retry_limit: int = 1):
        self.media_pipeline = media_pipeline
        self.state_dir = Path(state_dir)
        self.max_workers = max_workers
        self.retry_limit = retry_limit
        self._artifacts: dict[str, Any] = {}

    def run(self, *, authorized: bool = False, timeout_seconds: int = 3600,
            poll_seconds: int = 5, quality_scores: dict[str, dict[str, float]] | None = None,
            minimum_quality: float = 0.82) -> dict[str, Any]:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED", "executed_stages": []}

        quality_scores = quality_scores or {}
        stages = stages_from_media_pipeline(self.media_pipeline)
        scheduler = ParallelStageScheduler(
            stages, self.state_dir, max_workers=self.max_workers,
            retry_limit=self.retry_limit,
        )

        def execute(stage):
            deps = {name: self._artifacts[name] for name in stage.depends_on if name in self._artifacts}
            result = self.media_pipeline.runner.run(
                kind=stage.metadata["kind"],
                prompt=stage.metadata["prompt"],
                output_format=stage.metadata["output_format"],
                options={"dependencies": deps},
                authorized=True,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
            )
            if result.get("status") == "VERIFIED_COMPLETED":
                self._artifacts[stage.id] = result
            return result

        def verify(stage, result):
            if result.get("status") != "VERIFIED_COMPLETED":
                return {"verified": False, "reason": result.get("error", result.get("status"))}
            gate = self.media_pipeline.registry and __import__(
                "brain_v7.braincore_v2.media_quality_orchestrator",
                fromlist=["acceptance_gate"],
            ).acceptance_gate(quality_scores.get(stage.id, {}), minimum=minimum_quality)
            if not gate["accepted"]:
                return {
                    "verified": False,
                    "reason": "QUALITY_GATE",
                    "quality_gate": gate,
                }
            return {
                "verified": True,
                "evidence_ref": f"media://{self.media_pipeline.pipeline_id}/{stage.id}",
                "quality_gate": gate,
            }

        result = scheduler.run(execute, verify)
        result["artifacts"] = dict(self._artifacts)
        return result

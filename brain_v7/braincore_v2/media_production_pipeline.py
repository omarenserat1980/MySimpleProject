"""Chained multimedia production pipeline with quality orchestration."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .media_job_runner import MediaJobRunner
from .media_provider_registry import MediaProviderRegistry
from .media_quality_orchestrator import build_creative_brief, acceptance_gate
from .cinematic_director import build_plan as build_cinematic_plan, provider_prompts as cinematic_prompts


@dataclass(frozen=True)
class MediaStage:
    name: str
    kind: str
    prompt: str
    output_format: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class MediaPipeline:
    pipeline_id: str
    objective: str
    stages: tuple[MediaStage, ...]


def build_pipeline(objective: str, *, pipeline_id: str = "media-pipeline") -> MediaPipeline:
    objective = objective.strip()
    if not objective:
        raise ValueError("objective must not be empty")
    return MediaPipeline(
        pipeline_id=pipeline_id,
        objective=objective,
        stages=(
            MediaStage("IMAGE", "image", f"Create the cinematic master visual for: {objective}", "png"),
            MediaStage("VOICE", "audio", f"Create consistent Arabic cinematic narration for: {objective}", "mp3"),
            MediaStage(
                "VIDEO", "video",
                f"Create a cinematic short using the master visual, narration and shot plan for: {objective}. Shot plan: {shot_prompts}",
                "mp4", ("IMAGE", "VOICE"),
            ),
            MediaStage(
                "DESIGN", "design",
                f"Create the final cinematic promotional design package for: {objective}",
                "png", ("IMAGE", "VIDEO"),
            ),
        ),
    )


class MediaProductionPipeline:
    def __init__(self, registry: MediaProviderRegistry | None = None):
        self.registry = registry or MediaProviderRegistry()
        self.runner = MediaJobRunner(self.registry)

    def plan(self, objective: str) -> dict[str, Any]:
        pipeline = build_pipeline(objective)
        cinematic = build_cinematic_plan(objective)
        return {
            "pipeline": asdict(pipeline),
            "creative_brief": build_creative_brief(objective),
            "cinematic_director": asdict(cinematic),
            "shot_prompts": cinematic_prompts(cinematic),
        }

    def execute(
        self,
        objective: str,
        *,
        authorized: bool = False,
        pipeline_id: str = "media-pipeline",
        timeout_seconds: int = 3600,
        poll_seconds: int = 5,
        quality_scores: dict[str, dict[str, float]] | None = None,
        minimum_quality: float = 0.82,
    ) -> dict[str, Any]:
        pipeline = build_pipeline(objective, pipeline_id=pipeline_id)
        cinematic = build_cinematic_plan(objective)
        shot_prompts = cinematic_prompts(cinematic)
        if not authorized:
            return {
                "status": "AUTHORIZATION_REQUIRED",
                "pipeline": asdict(pipeline),
                "cinematic_director": asdict(cinematic),
                "shot_prompts": shot_prompts,
                "executed_stages": [],
            }

        artifacts: dict[str, Any] = {}
        executed: list[str] = []
        quality_scores = quality_scores or {}

        for stage in pipeline.stages:
            dependencies = {name: artifacts[name] for name in stage.depends_on if name in artifacts}
            result = self.runner.run(
                kind=stage.kind,
                prompt=stage.prompt,
                output_format=stage.output_format,
                options={"dependencies": dependencies},
                authorized=True,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
            )
            if result.get("status") != "VERIFIED_COMPLETED":
                return {
                    "status": "BLOCKED",
                    "failed_stage": stage.name,
                    "reason": result,
                    "pipeline": asdict(pipeline),
                    "artifacts": artifacts,
                    "executed_stages": executed,
                }

            gate = acceptance_gate(
                quality_scores.get(stage.name, {}),
                minimum=minimum_quality,
            )
            result["quality_gate"] = gate
            artifacts[stage.name] = result
            executed.append(stage.name)

            if not gate["accepted"]:
                return {
                    "status": "REFINE_REQUIRED",
                    "failed_stage": stage.name,
                    "reason": "QUALITY_GATE",
                    "pipeline": asdict(pipeline),
                    "artifacts": artifacts,
                    "executed_stages": executed,
                }

        return {
            "status": "VERIFIED_QUALITY",
            "pipeline": asdict(pipeline),
            "creative_brief": build_creative_brief(objective),
            "cinematic_director": asdict(cinematic),
            "shot_prompts": shot_prompts,
            "artifacts": artifacts,
            "executed_stages": executed,
        }


def snapshot() -> dict[str, Any]:
    return {
        "chain": ["IMAGE", "VOICE", "VIDEO", "DESIGN"],
        "dependency_aware": True,
        "provider_registry": True,
        "job_polling": True,
        "output_verification": True,
        "quality_gate": True,
        "cinematic_continuity": True,
        "cinematic_director": True,
        "shot_level_prompts": True,
        "credentials_in_source": False,
        "external_publication": "permission_gated",
    }

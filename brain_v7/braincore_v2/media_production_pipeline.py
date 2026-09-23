"""Chained multimedia production pipeline with injected provider routing."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

from .media_provider_registry import MediaProviderRegistry


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
            MediaStage("IMAGE", "image", f"Create the main visual for: {objective}", "png"),
            MediaStage("VOICE", "audio", f"Create Arabic voice narration for: {objective}", "mp3"),
            MediaStage(
                "VIDEO", "video",
                f"Create a short video combining the visual and narration for: {objective}",
                "mp4", ("IMAGE", "VOICE"),
            ),
            MediaStage(
                "DESIGN", "design",
                f"Create a final promotional design package for: {objective}",
                "png", ("IMAGE", "VIDEO"),
            ),
        ),
    )


class MediaProductionPipeline:
    def __init__(self, registry: MediaProviderRegistry | None = None):
        self.registry = registry or MediaProviderRegistry()

    def plan(self, objective: str) -> dict[str, Any]:
        return asdict(build_pipeline(objective))

    def execute(
        self,
        objective: str,
        *,
        authorized: bool = False,
        pipeline_id: str = "media-pipeline",
    ) -> dict[str, Any]:
        pipeline = build_pipeline(objective, pipeline_id=pipeline_id)
        if not authorized:
            return {
                "status": "AUTHORIZATION_REQUIRED",
                "pipeline": asdict(pipeline),
                "executed_stages": [],
            }

        artifacts: dict[str, Any] = {}
        executed: list[str] = []
        for stage in pipeline.stages:
            dependencies = {
                name: artifacts[name]
                for name in stage.depends_on
                if name in artifacts
            }
            result = self.registry.submit(
                kind=stage.kind,
                prompt=stage.prompt,
                output_format=stage.output_format,
                options={"dependencies": dependencies},
            )
            artifacts[stage.name] = result
            executed.append(stage.name)

            if result["status"] in {"FAILED", "NO_PROVIDER"}:
                return {
                    "status": "BLOCKED",
                    "failed_stage": stage.name,
                    "reason": result,
                    "pipeline": asdict(pipeline),
                    "artifacts": artifacts,
                    "executed_stages": executed,
                }

        return {
            "status": "SUBMITTED",
            "pipeline": asdict(pipeline),
            "artifacts": artifacts,
            "executed_stages": executed,
            "verification_required": True,
        }


def snapshot() -> dict[str, Any]:
    return {
        "chain": ["IMAGE", "VOICE", "VIDEO", "DESIGN"],
        "dependency_aware": True,
        "provider_registry": True,
        "credentials_in_source": False,
        "external_publication": "permission_gated",
    }

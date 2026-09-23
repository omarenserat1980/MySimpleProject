"""Chained image -> audio -> video -> design production pipeline.

Provider-neutral and permission-gated. Providers are injected by the runtime;
no credentials are stored here. The pipeline can plan a complete media
package and execute only explicitly authorized provider calls.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Mapping


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
                "VIDEO",
                "video",
                f"Create a short video combining the visual and narration for: {objective}",
                "mp4",
                ("IMAGE", "VOICE"),
            ),
            MediaStage(
                "DESIGN",
                "design",
                f"Create a final promotional design package for: {objective}",
                "png",
                ("IMAGE", "VIDEO"),
            ),
        ),
    )


class MediaProductionPipeline:
    def __init__(self, providers: Mapping[str, Callable[[MediaStage, Mapping[str, Any]], Any]] | None = None):
        self.providers = dict(providers or {})

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
            provider = self.providers.get(stage.kind)
            if provider is None:
                return {
                    "status": "PROVIDER_REQUIRED",
                    "missing_kind": stage.kind,
                    "pipeline": asdict(pipeline),
                    "artifacts": artifacts,
                    "executed_stages": executed,
                }
            dependencies = {name: artifacts[name] for name in stage.depends_on if name in artifacts}
            artifacts[stage.name] = provider(stage, dependencies)
            executed.append(stage.name)

        return {
            "status": "COMPLETED",
            "pipeline": asdict(pipeline),
            "artifacts": artifacts,
            "executed_stages": executed,
        }


def snapshot() -> dict[str, Any]:
    return {
        "chain": ["IMAGE", "VOICE", "VIDEO", "DESIGN"],
        "dependency_aware": True,
        "providers_required_for_execution": True,
        "credentials_in_source": False,
        "external_publication": "permission_gated",
    }

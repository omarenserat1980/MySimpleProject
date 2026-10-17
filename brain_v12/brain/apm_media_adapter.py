"""Adapter from the existing cinematic media pipeline to APM BUILD.

The adapter preserves the production pipeline's declared dependencies rather
than inventing new parallelism. IMAGE and VOICE can fan out; VIDEO waits for
both; DESIGN waits for IMAGE and VIDEO.
"""

from __future__ import annotations

from typing import Any

from .parallel_stage_scheduler import Stage


def stages_from_media_pipeline(pipeline: Any) -> list[Stage]:
    stages: list[Stage] = []
    for media_stage in pipeline.stages:
        metadata = {
            "label": media_stage.name,
            "kind": media_stage.kind,
            "prompt": media_stage.prompt,
            "output_format": media_stage.output_format,
            "pipeline_id": pipeline.pipeline_id,
            "objective": pipeline.objective,
        }
        stages.append(
            Stage(
                id=media_stage.name,
                depends_on=tuple(media_stage.depends_on),
                resource=None,
                metadata=metadata,
            )
        )
    return stages


def build_media_apm_profile(objective: str, pipeline_id: str = "media-pipeline") -> dict[str, Any]:
    from brain_v7.braincore_v2.media_production_pipeline import build_pipeline

    pipeline = build_pipeline(objective, pipeline_id=pipeline_id)
    stages = stages_from_media_pipeline(pipeline)
    return {
        "source": "brain_v7.braincore_v2.media_production_pipeline.build_pipeline",
        "pipeline_id": pipeline.pipeline_id,
        "objective": pipeline.objective,
        "stages": stages,
        "parallelism": {
            "fan_out": ["IMAGE", "VOICE"],
            "join": ["VIDEO"],
            "final": ["DESIGN"],
        },
    }

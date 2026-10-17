"""Adapter from CINEMATIC_V3_PRO shot plans to resumable APM film segments."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .film_segment_manager import FilmSegment


def segments_from_cinematic_plan(
    plan: dict[str, Any],
    *,
    shots_per_segment: int = 4,
    prefix: str = "CIN",
) -> list[FilmSegment]:
    shots = list(plan.get("shots", []))
    if not shots:
        raise ValueError("CINEMATIC_PLAN_HAS_NO_SHOTS")
    if shots_per_segment < 1:
        raise ValueError("shots_per_segment must be positive")

    segments: list[FilmSegment] = []
    cursor = 0.0
    for start in range(0, len(shots), shots_per_segment):
        group = shots[start:start + shots_per_segment]
        duration = sum(float(shot.get("duration_s", 0)) for shot in group)
        if duration <= 0:
            raise ValueError("CINEMATIC_SEGMENT_DURATION_INVALID")

        beat_ids = []
        for shot in group:
            sid = str(shot.get("id", ""))
            beat = sid.split("-", 1)[0]
            if beat and beat not in beat_ids:
                beat_ids.append(beat)

        fingerprint = "|".join(
            f"{shot.get('id')}:{shot.get('visual')}:{shot.get('voice')}:{shot.get('camera')}"
            for shot in group
        )
        index = len(segments)
        segments.append(FilmSegment(
            id=f"{prefix}-{index + 1:04d}",
            index=index,
            start_s=cursor,
            duration_s=duration,
            fingerprint=fingerprint,
        ))
        cursor += duration

    return segments


def cinematic_segment_manifest(plan: dict[str, Any], segments: list[FilmSegment]) -> dict[str, Any]:
    return {
        "plan_version": plan.get("version"),
        "title": plan.get("title"),
        "language": plan.get("language"),
        "target_minutes": plan.get("target_minutes"),
        "shot_count": len(plan.get("shots", [])),
        "segment_count": len(segments),
        "segments": [asdict(segment) for segment in segments],
        "continuity": plan.get("continuity", {}),
        "quality_gates": plan.get("quality_gates", {}),
        "status": "SEGMENT_PLAN_READY",
    }

"""OpenTimelineIO-compatible timeline export with a dependency-light fallback."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import opentimelineio as otio
except Exception:
    otio = None


def build_timeline(shots: list[dict[str, Any]], output_path: str | Path) -> dict[str, Any]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(shots, key=lambda s: str(s.get("shot_id", "")))
    if otio is None:
        payload = {
            "format": "otio-compatible-json",
            "warning": "OpenTimelineIO package is not installed; install it for native OTIO.",
            "clips": [
                {
                    "shot_id": s.get("shot_id"),
                    "video_ref": s.get("video_ref"),
                    "duration_s": s.get("duration_s"),
                    "scene_id": s.get("scene_id"),
                }
                for s in ordered
            ],
        }
        output.with_suffix(".json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "FALLBACK_TIMELINE", "path": str(output.with_suffix(".json")), "clips": len(ordered)}
    timeline = otio.schema.Timeline(name="Electronic Brain V6")
    track = otio.schema.Track(name="picture", kind="Video")
    for shot in ordered:
        duration = float(shot.get("duration_s") or 0)
        clip = otio.schema.Clip(name=str(shot.get("shot_id")), media_reference=otio.schema.ExternalReference(target_url=str(shot.get("video_ref", ""))))
        clip.source_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(0, 24),
            duration=otio.opentime.RationalTime(max(1, round(duration * 24)), 24),
        )
        track.append(clip)
    timeline.tracks.append(track)
    otio.adapters.write_to_file(timeline, str(output))
    return {"status": "OTIO_WRITTEN", "path": str(output), "clips": len(ordered)}

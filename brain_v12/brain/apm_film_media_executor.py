"""Segment-level media executor using the existing MediaJobRunner contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .film_segment_manager import FilmSegment, FilmSegmentManager


class APMFilmMediaExecutor:
    def __init__(self, media_pipeline: Any, *, state_dir: str, max_workers: int = 2,
                 retry_limit: int = 1):
        self.media_pipeline = media_pipeline
        self.state_dir = Path(state_dir)
        self.manager = FilmSegmentManager(
            max_workers=max_workers,
            retry_limit=retry_limit,
        )

    def run(self, segments: list[FilmSegment], *, authorized: bool = False,
            timeout_seconds: int = 3600, poll_seconds: int = 5) -> dict[str, Any]:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED", "segments": []}

        def execute(segment: FilmSegment) -> dict[str, Any]:
            result = self.media_pipeline.runner.run(
                kind="video",
                prompt=(
                    f"Render cinematic segment {segment.id}. "
                    f"Start={segment.start_s:.3f}s Duration={segment.duration_s:.3f}s. "
                    "Preserve the supplied CINEMATIC_V3_PRO shot continuity."
                ),
                output_format="mp4",
                options={
                    "segment_id": segment.id,
                    "segment_index": segment.index,
                    "start_s": segment.start_s,
                    "duration_s": segment.duration_s,
                },
                authorized=True,
                timeout_seconds=timeout_seconds,
                poll_seconds=poll_seconds,
            )
            return result

        def verify(segment: FilmSegment, result: dict[str, Any]) -> dict[str, Any]:
            if result.get("status") != "VERIFIED_COMPLETED":
                return {
                    "verified": False,
                    "reason": result.get("error", result.get("status")),
                }
            output = result.get("output") or result.get("output_url") or result.get("artifact")
            if not output:
                return {"verified": False, "reason": "SEGMENT_OUTPUT_MISSING"}
            return {
                "verified": True,
                "evidence_ref": f"film-segment://{segment.id}/verified",
                "output": output,
            }

        return self.manager.run(segments, str(self.state_dir), execute, verify)

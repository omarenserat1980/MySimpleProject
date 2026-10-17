"""Deterministic film segmentation for APM BUILD.

Segments are independent work units with stable time ranges. The manager
delegates execution/checkpointing to the APM chunk scheduler and assembles only
verified segment results in timeline order.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable

from .apm_chunk_scheduler import Chunk, ChunkScheduler


@dataclass(frozen=True)
class FilmSegment:
    id: str
    index: int
    start_s: float
    duration_s: float
    fingerprint: str = ""


class FilmSegmentManager:
    def __init__(self, *, segment_duration_s: float = 30.0, max_workers: int = 4,
                 retry_limit: int = 1):
        if segment_duration_s <= 0:
            raise ValueError("segment_duration_s must be positive")
        self.segment_duration_s = float(segment_duration_s)
        self.max_workers = max_workers
        self.retry_limit = retry_limit

    def plan(self, target_seconds: float, *, prefix: str = "SEG") -> list[FilmSegment]:
        if target_seconds <= 0:
            raise ValueError("target_seconds must be positive")
        segments: list[FilmSegment] = []
        index = 0
        start = 0.0
        while start < target_seconds:
            duration = min(self.segment_duration_s, target_seconds - start)
            segments.append(FilmSegment(
                id=f"{prefix}-{index + 1:04d}",
                index=index,
                start_s=start,
                duration_s=duration,
                fingerprint=f"{prefix}:{index}:{start:.3f}:{duration:.3f}",
            ))
            index += 1
            start += duration
        return segments

    def run(
        self,
        segments: list[FilmSegment],
        state_dir: str,
        executor: Callable[[FilmSegment], dict[str, Any]],
        verifier: Callable[[FilmSegment, dict[str, Any]], dict[str, Any] | bool],
    ) -> dict[str, Any]:
        chunks = [
            Chunk(
                id=segment.id,
                stage_id="VIDEO",
                index=segment.index,
                input_fingerprint=segment.fingerprint,
            )
            for segment in segments
        ]
        by_id = {segment.id: segment for segment in segments}

        def chunk_executor(chunk: Chunk) -> dict[str, Any]:
            return executor(by_id[chunk.id])

        def chunk_verifier(chunk: Chunk, result: dict[str, Any]) -> dict[str, Any] | bool:
            return verifier(by_id[chunk.id], result)

        result = ChunkScheduler(
            chunks, state_dir, max_workers=self.max_workers,
            retry_limit=self.retry_limit,
        ).run(chunk_executor, chunk_verifier)

        ordered = sorted(
            (result["evidence"][sid] for sid in result["completed"] if sid in result["evidence"]),
            key=lambda item: by_id[item["chunk_id"]].index,
        )
        result["segments"] = [asdict(by_id[item["chunk_id"]]) for item in ordered]
        result["assembly_order"] = [item["id"] for item in sorted(segments, key=lambda s: s.index)]
        result["ready_for_assembly"] = result["status"] == "VERIFIED_COMPLETED"
        return result

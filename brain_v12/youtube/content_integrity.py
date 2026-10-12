"""Content identity, deduplication, and experiment integrity primitives."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentFingerprint:
    video_id: str
    niche: str
    title_angle: str
    script_fingerprint: str
    asset_fingerprint: str

    def canonical(self) -> str:
        return json.dumps(
            {
                "video_id": self.video_id,
                "niche": self.niche,
                "title_angle": self.title_angle,
                "script_fingerprint": self.script_fingerprint,
                "asset_fingerprint": self.asset_fingerprint,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


def duplicate_content(
    candidate: ContentFingerprint,
    existing: list[ContentFingerprint],
) -> bool:
    return any(candidate.digest == item.digest for item in existing)


@dataclass(frozen=True)
class ExperimentRecord:
    experiment_id: str
    video_id: str
    hypothesis: str
    variant: str
    baseline_id: str | None = None

    def __post_init__(self) -> None:
        if not self.experiment_id or not self.video_id or not self.hypothesis or not self.variant:
            raise ValueError("experiment identity fields are required")


def unique_experiments(records: list[ExperimentRecord]) -> list[ExperimentRecord]:
    seen: set[str] = set()
    result: list[ExperimentRecord] = []
    for record in records:
        if record.experiment_id in seen:
            continue
        seen.add(record.experiment_id)
        result.append(record)
    return result

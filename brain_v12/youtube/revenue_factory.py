"""Deterministic YouTube revenue-factory planning primitives.

Planning only: no publishing, payment movement, impersonation, or revenue claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ContentState(str, Enum):
    IDEA = "IDEA"
    SELECTED = "SELECTED"
    SCRIPTED = "SCRIPTED"
    ASSETS_READY = "ASSETS_READY"
    RENDERED = "RENDERED"
    QC_PASSED = "QC_PASSED"
    PUBLISH_READY = "PUBLISH_READY"
    PUBLISHED = "PUBLISHED"
    MEASURED = "MEASURED"


@dataclass(frozen=True)
class VideoCandidate:
    video_id: str
    niche: str
    title_angle: str
    expected_demand: float
    production_cost: float
    production_risk: float
    originality: float

    def __post_init__(self) -> None:
        if not self.video_id or not self.niche or not self.title_angle:
            raise ValueError("video identity fields are required")
        for name in ("expected_demand", "production_cost", "production_risk", "originality"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class ContentDecision:
    selected: bool
    score: float
    reason: str


def rank_video(candidate: VideoCandidate) -> ContentDecision:
    score = (
        candidate.expected_demand * 0.40
        + candidate.originality * 0.30
        + (1 - candidate.production_cost) * 0.20
        + (1 - candidate.production_risk) * 0.10
    )
    if candidate.originality < 0.40:
        return ContentDecision(False, score, "ORIGINALITY_TOO_LOW")
    if candidate.production_risk > 0.80:
        return ContentDecision(False, score, "PRODUCTION_RISK_TOO_HIGH")
    return ContentDecision(score >= 0.55, score, "SELECTED" if score >= 0.55 else "BELOW_THRESHOLD")


def next_content_state(state: ContentState, *, qc_passed: bool = False) -> ContentState:
    if state is ContentState.IDEA:
        return ContentState.SELECTED
    if state is ContentState.SELECTED:
        return ContentState.SCRIPTED
    if state is ContentState.SCRIPTED:
        return ContentState.ASSETS_READY
    if state is ContentState.ASSETS_READY:
        return ContentState.RENDERED
    if state is ContentState.RENDERED:
        return ContentState.QC_PASSED if qc_passed else ContentState.RENDERED
    if state is ContentState.QC_PASSED:
        return ContentState.PUBLISH_READY
    if state is ContentState.PUBLISH_READY:
        return ContentState.PUBLISHED
    if state is ContentState.PUBLISHED:
        return ContentState.MEASURED
    return state

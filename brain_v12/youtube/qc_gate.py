"""Technical/cinematic QC and publishing authorization boundaries.

Pure checks only; no upload or external side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PublishDecision(str, Enum):
    HOLD = "HOLD"
    READY = "READY"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class QcReport:
    technical_pass: bool
    cinematic_pass: bool
    duration_seconds: float
    has_audio: bool
    has_video: bool
    originality_confirmed: bool
    policy_risk: float = 0.0

    def __post_init__(self) -> None:
        if self.duration_seconds < 0:
            raise ValueError("duration cannot be negative")
        if not 0 <= self.policy_risk <= 1:
            raise ValueError("policy_risk must be between 0 and 1")


def evaluate_publish_gate(
    report: QcReport,
    *,
    minimum_duration_seconds: float = 1.0,
    maximum_policy_risk: float = 0.50,
) -> PublishDecision:
    if report.duration_seconds < minimum_duration_seconds:
        return PublishDecision.BLOCK
    if not report.has_video or not report.has_audio:
        return PublishDecision.BLOCK
    if not report.technical_pass or not report.cinematic_pass:
        return PublishDecision.BLOCK
    if not report.originality_confirmed:
        return PublishDecision.BLOCK
    if report.policy_risk > maximum_policy_risk:
        return PublishDecision.HOLD
    return PublishDecision.READY

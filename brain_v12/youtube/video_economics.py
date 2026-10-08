"""Economic decision layer for individual YouTube videos.

This module estimates production economics only. Estimates are never revenue.
No publishing, payment movement, or external side effects occur here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VideoEconomicAction(str, Enum):
    PRODUCE = "PRODUCE"
    HOLD = "HOLD"
    KILL = "KILL"


@dataclass(frozen=True)
class VideoEconomics:
    video_id: str
    production_hours: float
    tool_cost_usd: float
    asset_cost_usd: float
    expected_views: int
    expected_rpm_usd: float
    success_probability: float
    learning_value: float = 0.0

    def __post_init__(self) -> None:
        if not self.video_id:
            raise ValueError("video_id is required")
        if self.production_hours < 0 or self.tool_cost_usd < 0 or self.asset_cost_usd < 0:
            raise ValueError("production inputs cannot be negative")
        if self.expected_views < 0 or self.expected_rpm_usd < 0:
            raise ValueError("view and RPM estimates cannot be negative")
        if not 0 <= self.success_probability <= 1:
            raise ValueError("success_probability must be between 0 and 1")
        if not 0 <= self.learning_value <= 1:
            raise ValueError("learning_value must be between 0 and 1")

    @property
    def direct_cost_usd(self) -> float:
        return self.tool_cost_usd + self.asset_cost_usd

    @property
    def expected_ad_value_usd(self) -> float:
        return self.expected_views / 1000 * self.expected_rpm_usd * self.success_probability

    @property
    def expected_net_value_usd(self) -> float:
        return self.expected_ad_value_usd - self.direct_cost_usd

    @property
    def break_even_views(self) -> int | None:
        if self.expected_rpm_usd <= 0:
            return None
        return int((self.direct_cost_usd / self.expected_rpm_usd) * 1000 + 0.999999)

    @property
    def risk_adjusted_score(self) -> float:
        return self.expected_net_value_usd + self.learning_value

@dataclass(frozen=True)
class VideoEconomicDecision:
    action: VideoEconomicAction
    score: float
    reason: str


def decide_video_economics(
    economics: VideoEconomics,
    *,
    minimum_expected_net_usd: float = 0.0,
    maximum_direct_cost_usd: float = 5.0,
) -> VideoEconomicDecision:
    if economics.direct_cost_usd > maximum_direct_cost_usd:
        return VideoEconomicDecision(
            VideoEconomicAction.KILL,
            economics.risk_adjusted_score,
            "DIRECT_COST_TOO_HIGH",
        )
    if economics.expected_views == 0 or economics.expected_rpm_usd == 0:
        if economics.learning_value >= 0.75:
            return VideoEconomicDecision(
                VideoEconomicAction.HOLD,
                economics.risk_adjusted_score,
                "LEARNING_EXPERIMENT_ONLY",
            )
        return VideoEconomicDecision(
            VideoEconomicAction.KILL,
            economics.risk_adjusted_score,
            "NO_MONETARY_SIGNAL",
        )
    if economics.expected_net_value_usd >= minimum_expected_net_usd:
        return VideoEconomicDecision(
            VideoEconomicAction.PRODUCE,
            economics.risk_adjusted_score,
            "POSITIVE_EXPECTED_VALUE",
        )
    if economics.learning_value >= 0.50:
        return VideoEconomicDecision(
            VideoEconomicAction.HOLD,
            economics.risk_adjusted_score,
            "LEARNING_VALUE_OFFSETS_WEAK_EXPECTED_VALUE",
        )
    return VideoEconomicDecision(
        VideoEconomicAction.KILL,
        economics.risk_adjusted_score,
        "NEGATIVE_EXPECTED_VALUE",
    )

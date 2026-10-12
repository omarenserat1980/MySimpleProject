"""Channel strategy and experiment selection for the YouTube Revenue Factory.

Pure decision layer. It never publishes, spends money, or records revenue.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelProfile:
    channel_id: str
    language: str
    niche: str
    audience_fit: float
    demand: float
    competition: float
    production_fit: float
    monetization_fit: float
    originality_headroom: float

    def __post_init__(self) -> None:
        if not self.channel_id or not self.language or not self.niche:
            raise ValueError("channel identity fields are required")
        for name in (
            "audience_fit", "demand", "competition", "production_fit",
            "monetization_fit", "originality_headroom",
        ):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class ChannelDecision:
    viable: bool
    score: float
    reasons: tuple[str, ...]


def evaluate_channel(profile: ChannelProfile) -> ChannelDecision:
    score = (
        profile.audience_fit * 0.20
        + profile.demand * 0.25
        + (1 - profile.competition) * 0.15
        + profile.production_fit * 0.15
        + profile.monetization_fit * 0.15
        + profile.originality_headroom * 0.10
    )
    reasons: list[str] = []
    if profile.audience_fit < 0.40:
        reasons.append("WEAK_AUDIENCE_FIT")
    if profile.originality_headroom < 0.40:
        reasons.append("LOW_ORIGINALITY_HEADROOM")
    if profile.production_fit < 0.40:
        reasons.append("WEAK_PRODUCTION_FIT")
    viable = not reasons and score >= 0.55
    if viable:
        reasons.append("CHANNEL_VIABLE")
    elif not reasons:
        reasons.append("BELOW_CHANNEL_THRESHOLD")
    return ChannelDecision(viable, score, tuple(reasons))


@dataclass(frozen=True)
class ExperimentResult:
    experiment_id: str
    impressions: int
    views: int
    average_view_duration_seconds: float
    published_videos: int

    @property
    def ctr_proxy(self) -> float:
        return self.views / self.impressions if self.impressions else 0.0

    @property
    def views_per_video(self) -> float:
        return self.views / self.published_videos if self.published_videos else 0.0

    @property
    def watch_seconds_per_impression(self) -> float:
        return self.views * self.average_view_duration_seconds / self.impressions if self.impressions else 0.0


def choose_experiment(results: list[ExperimentResult]) -> str:
    if not results:
        return "BASELINE"
    ranked = sorted(
        results,
        key=lambda item: (
            item.watch_seconds_per_impression,
            item.views_per_video,
            item.ctr_proxy,
        ),
        reverse=True,
    )
    return ranked[0].experiment_id

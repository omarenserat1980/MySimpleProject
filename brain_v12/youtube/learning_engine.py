"""Evidence-based learning and expansion gates for the YouTube factory.

Pure decision layer. Historical observations are immutable inputs; no revenue is created.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExpansionAction(str, Enum):
    CONTINUE = "CONTINUE"
    ITERATE = "ITERATE"
    HOLD = "HOLD"
    EXPAND = "EXPAND"


@dataclass(frozen=True)
class Measurement:
    experiment_id: str
    impressions: int
    views: int
    average_view_duration_seconds: float
    subscribers_gained: int = 0

    def __post_init__(self) -> None:
        if not self.experiment_id:
            raise ValueError("experiment_id is required")
        if self.impressions < 0 or self.views < 0:
            raise ValueError("metrics cannot be negative")
        if self.views > self.impressions and self.impressions:
            raise ValueError("views cannot exceed impressions")
        if self.average_view_duration_seconds < 0:
            raise ValueError("average view duration cannot be negative")
        if self.subscribers_gained < 0:
            raise ValueError("subscribers gained cannot be negative")

    @property
    def watch_efficiency(self) -> float:
        if not self.impressions:
            return 0.0
        return self.views * self.average_view_duration_seconds / self.impressions


@dataclass(frozen=True)
class LearningSnapshot:
    experiments: int
    total_impressions: int
    total_views: int
    best_watch_efficiency: float
    repeat_winner_count: int


def summarize_learning(measurements: list[Measurement]) -> LearningSnapshot:
    if not measurements:
        return LearningSnapshot(0, 0, 0, 0.0, 0)

    ordered = sorted(measurements, key=lambda x: x.watch_efficiency, reverse=True)
    best = ordered[0].watch_efficiency
    winner = ordered[0].experiment_id
    repeats = sum(m.experiment_id == winner for m in measurements)

    return LearningSnapshot(
        experiments=len(measurements),
        total_impressions=sum(m.impressions for m in measurements),
        total_views=sum(m.views for m in measurements),
        best_watch_efficiency=best,
        repeat_winner_count=repeats,
    )


def expansion_gate(
    snapshot: LearningSnapshot,
    *,
    minimum_experiments: int = 5,
    minimum_impressions: int = 5000,
    minimum_repeat_winners: int = 2,
) -> ExpansionAction:
    if snapshot.experiments == 0:
        return ExpansionAction.HOLD
    if snapshot.experiments < minimum_experiments:
        return ExpansionAction.CONTINUE
    if snapshot.total_impressions < minimum_impressions:
        return ExpansionAction.CONTINUE
    if snapshot.repeat_winner_count < minimum_repeat_winners:
        return ExpansionAction.ITERATE
    return ExpansionAction.EXPAND

"""Adaptive priority engine for the electronic brain.

Uses recorded cycle outcomes to adjust future development priorities. It is
local decision support: it does not grant permissions or perform external
financial/legal actions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class PrioritySignal:
    domain: str
    opportunity_value: float = 0.0
    speed: float = 0.0
    outcome: float = 0.0
    repeatability: float = 0.0

    @property
    def score(self) -> float:
        return (
            max(0.0, self.opportunity_value) * 0.35
            + max(0.0, self.speed) * 0.20
            + max(0.0, self.outcome) * 0.30
            + max(0.0, self.repeatability) * 0.15
        )


def rank_signals(signals: Iterable[PrioritySignal]) -> list[dict]:
    return [
        asdict(s) | {"score": round(s.score, 4)}
        for s in sorted(signals, key=lambda x: x.score, reverse=True)
    ]


def next_focus(
    signals: Iterable[PrioritySignal],
    *,
    fallback_domain: str = "software_engineering",
) -> dict:
    ranked = rank_signals(signals)
    if not ranked:
        return {
            "domain": fallback_domain,
            "reason": "NO_FEEDBACK",
            "ranked": [],
        }
    best = ranked[0]
    return {
        "domain": best["domain"],
        "reason": "HIGHEST_ADAPTIVE_PRIORITY",
        "score": best["score"],
        "ranked": ranked,
    }


def feedback_from_cycle(
    domain: str,
    *,
    opportunity_value: float = 0.0,
    speed: float = 0.0,
    outcome: float = 0.0,
    repeatability: float = 0.0,
) -> PrioritySignal:
    return PrioritySignal(
        domain=domain,
        opportunity_value=opportunity_value,
        speed=speed,
        outcome=outcome,
        repeatability=repeatability,
    )

"""Opportunity acceleration layer.

Optimizes the queue for speed-to-first-dollar while preserving evidence gates.
It does not submit applications, send proposals, or move money.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class AccelerationCandidate:
    lead_id: str
    title: str
    service: str
    offered_jod: float
    effort_hours: float
    evidence: float = 0.0
    fit: float = 0.0
    friction: float = 0.0
    risk: float = 0.0
    response_hours: float = 24.0
    deadline_hours: float | None = None

    @property
    def value_per_hour(self) -> float:
        return self.offered_jod / max(self.effort_hours, 0.25)

    @property
    def time_to_first_dollar_hours(self) -> float:
        return max(self.response_hours, 0.25) + max(self.effort_hours, 0.25)

    @property
    def acceleration_score(self) -> float:
        # Speed matters, but evidence/fit/risk gates remain dominant.
        speed = 30.0 / max(self.time_to_first_dollar_hours, 0.25)
        economics = min(self.value_per_hour, 100.0) * 0.30
        quality = (self.evidence * 20.0 + self.fit * 15.0)
        friction_penalty = self.friction * 10.0
        risk_penalty = self.risk * 20.0
        urgency_bonus = 8.0 if self.deadline_hours is not None and self.deadline_hours <= 24 else 0.0
        return round(speed + economics + quality + urgency_bonus - friction_penalty - risk_penalty, 2)

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["value_per_hour"] = round(self.value_per_hour, 2)
        row["time_to_first_dollar_hours"] = round(self.time_to_first_dollar_hours, 2)
        row["acceleration_score"] = self.acceleration_score
        return row


def rank_for_speed(candidates: Iterable[AccelerationCandidate]) -> list[dict[str, Any]]:
    """Return the fastest/economically strongest candidates first.

    Candidates lacking minimum evidence or with high risk are retained only as
    research items, never as execution-ready work.
    """
    rows = sorted(candidates, key=lambda x: x.acceleration_score, reverse=True)
    result = []
    for item in rows:
        row = item.to_dict()
        if item.evidence < 0.6:
            row["gate"] = "RESEARCH_REQUIRED"
        elif item.fit < 0.5:
            row["gate"] = "LOW_FIT"
        elif item.risk > 0.5:
            row["gate"] = "REVIEW_REQUIRED"
        else:
            row["gate"] = "READY_FOR_USER_SUBMISSION"
        result.append(row)
    return result


def build_parallel_plan(candidates: Iterable[AccelerationCandidate], lanes: int = 3) -> dict[str, Any]:
    """Create a bounded parallel research/execution queue.

    This reduces idle time by preparing several independent opportunities,
    while external submission remains a user-controlled side effect.
    """
    lanes = max(1, min(int(lanes), 5))
    ranked = rank_for_speed(candidates)
    ready = [x for x in ranked if x["gate"] == "READY_FOR_USER_SUBMISSION"]
    research = [x for x in ranked if x["gate"] != "READY_FOR_USER_SUBMISSION"]
    selected = ready[:lanes]
    return {
        "status": "READY" if selected else "RESEARCH_REQUIRED",
        "lanes": lanes,
        "parallel_candidates": selected,
        "research_backlog": research,
        "execution_requires_user_submission": True,
        "realized_profit_jod": 0.0,
        "profit_status": "NO_VERIFIED_PAYMENT",
    }


def freshness_hours(observed_at: str | float | int | None) -> float | None:
    """Return age in hours for an ISO timestamp or epoch timestamp."""
    if observed_at is None:
        return None
    try:
        if isinstance(observed_at, (int, float)):
            stamp = float(observed_at)
        else:
            stamp = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00")).timestamp()
        return max(0.0, (datetime.now(timezone.utc).timestamp() - stamp) / 3600.0)
    except (TypeError, ValueError, OverflowError):
        return None

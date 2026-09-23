"""Closed-loop coordinator for the 100,000 USD revenue objective.

It consumes already-collected lead data, applies evidence/speed/economics gates,
and emits a preparation queue. It never submits jobs, signs contracts, or moves
money. Realized revenue is counted only from verified payment evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

from .revenue_target_engine import RevenueOutcome, target_status, verified_revenue


@dataclass(frozen=True)
class TargetCandidate:
    lead_id: str
    title: str
    service: str
    value_usd: float
    effort_hours: float
    evidence: float
    fit: float
    risk: float
    repeatable: bool = False

    @property
    def hourly_value(self) -> float:
        return self.value_usd / self.effort_hours if self.effort_hours > 0 else 0.0

    @property
    def priority(self) -> float:
        return round(
            self.hourly_value * (0.5 + 0.25 * self.evidence + 0.25 * self.fit)
            * (1.15 if self.repeatable else 1.0)
            * max(0.0, 1.0 - self.risk),
            4,
        )


def rank_candidates(candidates: Iterable[TargetCandidate]) -> list[TargetCandidate]:
    return sorted(candidates, key=lambda x: x.priority, reverse=True)


def preparation_gate(candidate: TargetCandidate) -> str:
    if candidate.value_usd <= 0 or candidate.effort_hours <= 0:
        return "BLOCKED_BAD_ECONOMICS"
    if candidate.evidence < 0.6:
        return "RESEARCH_REQUIRED"
    if candidate.fit < 0.5:
        return "LOW_FIT"
    if candidate.risk > 0.5:
        return "REVIEW_REQUIRED"
    return "READY_FOR_PREPARATION"


def orchestrate(
    candidates: Iterable[TargetCandidate],
    outcomes: Iterable[RevenueOutcome] = (),
    max_queue: int = 5,
) -> dict:
    ranked = rank_candidates(candidates)
    queue = [
        {
            **asdict(c),
            "priority": c.priority,
            "gate": preparation_gate(c),
            "external_submission_required": True,
            "payment_confirmation_required": True,
        }
        for c in ranked[:max(1, min(max_queue, 20))]
        if preparation_gate(c) == "READY_FOR_PREPARATION"
    ]
    state = target_status(outcomes)
    return {
        "target": state,
        "verified_revenue_usd": verified_revenue(outcomes),
        "queue": queue,
        "queue_count": len(queue),
        "external_submission_performed": False,
        "money_movement_performed": False,
        "next_action": "PREPARE_TOP_CANDIDATE" if queue else "RESEARCH_MORE_VERIFIED_OPPORTUNITIES",
        "repeatability_focus": True,
    }

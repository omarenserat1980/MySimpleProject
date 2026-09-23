"""Safe economic controller for prioritizing work, not moving money."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .governance import evaluate_action
from .revenue_engine import Opportunity

@dataclass(frozen=True)
class WorkDecision:
    opportunity: str
    expected_jod: float
    effort_hours: float
    expected_hourly_jod: float
    action: str
    requires_approval: bool
    rationale: str

def evaluate(opportunity: Opportunity, *, direct_cost_jod: float = 0.0) -> WorkDecision:
    gross=max(0.0, opportunity.expected_jod-float(direct_cost_jod))
    hourly=gross/max(opportunity.effort_hours,0.25)
    policy=evaluate_action("submit_job")
    return WorkDecision(
        opportunity=opportunity.name,
        expected_jod=round(gross,2),
        effort_hours=opportunity.effort_hours,
        expected_hourly_jod=round(hourly,2),
        action="submit_job",
        requires_approval=policy.requires_approval,
        rationale="Prioritize by expected unit economics; payment is unverified until recorded as paid.",
    )

def rank_for_execution(items: list[Opportunity], direct_cost_jod: float=0.0) -> list[dict[str,Any]]:
    decisions=[evaluate(x,direct_cost_jod=direct_cost_jod) for x in items]
    return [d.__dict__ for d in sorted(decisions,key=lambda d:(d.expected_hourly_jod,d.expected_jod),reverse=True)]

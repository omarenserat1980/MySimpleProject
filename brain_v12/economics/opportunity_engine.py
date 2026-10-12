"""Deterministic opportunity lifecycle, deduplication, ranking, and revenue guardrails."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class OpportunityState(str, Enum):
    DISCOVERED = "DISCOVERED"
    VERIFIED = "VERIFIED"
    SHORTLISTED = "SHORTLISTED"
    APPLICATION_READY = "APPLICATION_READY"
    APPLIED = "APPLIED"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    expected_pay: float
    acceptance_probability: float
    brain_assistance: float
    time_hours: float
    entry_friction: float
    risk: float
    state: OpportunityState = OpportunityState.DISCOVERED


@dataclass(frozen=True)
class LifecycleEvent:
    opportunity_id: str
    from_state: OpportunityState
    to_state: OpportunityState
    evidence_ref: str | None = None


def score(opportunity: Opportunity) -> float:
    """Return a comparable score; invalid estimates fail closed."""
    if opportunity.expected_pay < 0 or opportunity.time_hours < 0:
        raise ValueError("pay/time cannot be negative")
    for value in (
        opportunity.acceptance_probability,
        opportunity.brain_assistance,
        opportunity.entry_friction,
        opportunity.risk,
    ):
        if not 0 <= value <= 1:
            raise ValueError("normalized opportunity inputs must be between 0 and 1")
    denominator = opportunity.time_hours + opportunity.entry_friction + opportunity.risk
    if denominator <= 0:
        return 0.0
    return (
        opportunity.expected_pay
        * opportunity.acceptance_probability
        * opportunity.brain_assistance
    ) / denominator


def rank_opportunities(opportunities: Iterable[Opportunity]) -> list[tuple[Opportunity, float]]:
    """Rank opportunities by descending score, then stable ID."""
    ranked = [(item, score(item)) for item in opportunities]
    return sorted(ranked, key=lambda pair: (-pair[1], pair[0].opportunity_id))


def deduplicate_opportunities(opportunities: Iterable[Opportunity]) -> list[Opportunity]:
    """Keep one opportunity per stable ID; first occurrence wins."""
    seen: set[str] = set()
    result: list[Opportunity] = []
    for opportunity in opportunities:
        if not opportunity.opportunity_id:
            raise ValueError("opportunity_id cannot be empty")
        if opportunity.opportunity_id in seen:
            continue
        seen.add(opportunity.opportunity_id)
        result.append(opportunity)
    return result


def transition_allowed(current: OpportunityState, target: OpportunityState) -> bool:
    order = list(OpportunityState)
    try:
        return order.index(target) == order.index(current) + 1
    except ValueError:
        return False


def create_transition(
    opportunity: Opportunity,
    target: OpportunityState,
    evidence_ref: str | None = None,
) -> tuple[Opportunity, LifecycleEvent]:
    """Advance exactly one lifecycle state and emit an auditable event."""
    if not transition_allowed(opportunity.state, target):
        raise ValueError(
            f"invalid transition: {opportunity.state.value} -> {target.value}"
        )
    updated = Opportunity(
        opportunity.opportunity_id,
        opportunity.expected_pay,
        opportunity.acceptance_probability,
        opportunity.brain_assistance,
        opportunity.time_hours,
        opportunity.entry_friction,
        opportunity.risk,
        target,
    )
    return updated, LifecycleEvent(
        opportunity_id=opportunity.opportunity_id,
        from_state=opportunity.state,
        to_state=target,
        evidence_ref=evidence_ref,
    )


def can_record_confirmed_revenue(
    state: OpportunityState, payment_evidence: bool
) -> bool:
    """Revenue is confirmed only after payment verification evidence exists."""
    return state is OpportunityState.PAYMENT_VERIFIED and payment_evidence

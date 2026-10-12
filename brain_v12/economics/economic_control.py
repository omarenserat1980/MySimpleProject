"""Economic causality, attribution and control-plane primitives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EconomicState(str, Enum):
    POTENTIAL = "POTENTIAL"
    VERIFIED = "VERIFIED"
    SELECTED = "SELECTED"
    COMMITTED = "COMMITTED"
    WORKING = "WORKING"
    DELIVERED = "DELIVERED"
    RECEIVABLE = "RECEIVABLE"
    PAID = "PAID"
    PROVEN = "PROVEN"
    SETTLED = "SETTLED"


_ALLOWED: dict[EconomicState, EconomicState | None] = {
    EconomicState.POTENTIAL: EconomicState.VERIFIED,
    EconomicState.VERIFIED: EconomicState.SELECTED,
    EconomicState.SELECTED: EconomicState.COMMITTED,
    EconomicState.COMMITTED: EconomicState.WORKING,
    EconomicState.WORKING: EconomicState.DELIVERED,
    EconomicState.DELIVERED: EconomicState.RECEIVABLE,
    EconomicState.RECEIVABLE: EconomicState.PAID,
    EconomicState.PAID: EconomicState.PROVEN,
    EconomicState.PROVEN: EconomicState.SETTLED,
    EconomicState.SETTLED: None,
}


@dataclass(frozen=True)
class CausalChain:
    opportunity_id: str
    application_id: str
    task_id: str
    delivery_id: str
    payment_evidence_id: str

    def is_complete(self) -> bool:
        return all(
            value.strip()
            for value in (
                self.opportunity_id,
                self.application_id,
                self.task_id,
                self.delivery_id,
                self.payment_evidence_id,
            )
        )


def transition_allowed(current: EconomicState, target: EconomicState) -> bool:
    return _ALLOWED[current] == target


def require_complete_causality(chain: CausalChain) -> CausalChain:
    if not chain.is_complete():
        raise ValueError("incomplete economic causal chain")
    return chain


@dataclass(frozen=True)
class RevenueAttribution:
    revenue_event_id: str
    opportunity_id: str
    opportunity_class: str
    channel: str
    amount: float
    currency: str

    def is_valid(self) -> bool:
        return (
            bool(self.revenue_event_id.strip())
            and bool(self.opportunity_id.strip())
            and bool(self.opportunity_class.strip())
            and bool(self.channel.strip())
            and self.amount > 0
            and bool(self.currency.strip())
        )


@dataclass(frozen=True)
class EconomicBudget:
    time_hours: float
    retry_count: int
    risk_score: float

    def allows(self, *, time_hours: float, retries: int, risk_score: float) -> bool:
        return (
            time_hours >= 0
            and retries >= 0
            and 0 <= risk_score <= 1
            and time_hours <= self.time_hours
            and retries <= self.retry_count
            and risk_score <= self.risk_score
        )

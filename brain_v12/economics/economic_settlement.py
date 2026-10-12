"""Deterministic economic settlement and ledger rebuild primitives."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .economic_control import CausalChain, require_complete_causality
from .revenue_integrity import RevenueProof


@dataclass(frozen=True)
class SettlementEvent:
    revenue_event_id: str
    proof: RevenueProof
    causality: CausalChain


@dataclass(frozen=True)
class LedgerSnapshot:
    currency: str
    confirmed_revenue: Decimal
    event_count: int


def settle_event(event: SettlementEvent) -> SettlementEvent:
    if not event.revenue_event_id.strip():
        raise ValueError("missing revenue_event_id")
    require_complete_causality(event.causality)
    if event.proof.opportunity_id != event.causality.opportunity_id:
        raise ValueError("revenue proof does not match causal opportunity")
    if event.proof.amount <= 0:
        raise ValueError("revenue amount must be positive")
    return event


def rebuild_ledger(
    events: list[SettlementEvent],
    *,
    currency: str = "USD",
) -> LedgerSnapshot:
    if not currency.strip():
        raise ValueError("currency is required")

    seen_event_ids: set[str] = set()
    seen_evidence_ids: set[str] = set()
    total = Decimal("0")

    for raw_event in events:
        event = settle_event(raw_event)
        if event.revenue_event_id in seen_event_ids:
            raise ValueError("duplicate revenue event")
        if event.proof.evidence_id in seen_evidence_ids:
            raise ValueError("duplicate payment evidence")

        event_currency = event.proof.currency.upper()
        if event_currency != currency.upper():
            raise ValueError("mixed currencies require separate ledgers")

        seen_event_ids.add(event.revenue_event_id)
        seen_evidence_ids.add(event.proof.evidence_id)
        total += Decimal(str(event.proof.amount))

    return LedgerSnapshot(
        currency=currency.upper(),
        confirmed_revenue=total,
        event_count=len(events),
    )

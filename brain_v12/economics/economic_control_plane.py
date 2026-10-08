"""Single economic control-plane facade.

This module composes the deterministic economic layers without introducing
workers, background tasks, money movement, or application submission.
"""

from __future__ import annotations

from dataclasses import dataclass

from .economic_control import CausalChain, EconomicBudget, RevenueAttribution
from .economic_governor import EconomicSignal, GovernorDecision, govern
from .revenue_gate import PaymentEvidence
from .revenue_integrity import IntegrityResult, verify_payment_evidence
from .economic_settlement import SettlementEvent, LedgerSnapshot, rebuild_ledger


@dataclass(frozen=True)
class EconomicControlResult:
    governor: GovernorDecision
    evidence: IntegrityResult


def evaluate_control(
    *,
    signal: EconomicSignal,
    budget: EconomicBudget,
    evidence: PaymentEvidence,
    existing_evidence_ids: set[str] | None = None,
    existing_evidence_hashes: set[str] | None = None,
) -> EconomicControlResult:
    """Evaluate one economic path deterministically."""
    decision = govern(signal, budget)
    evidence_result = verify_payment_evidence(
        evidence,
        existing_evidence_ids=existing_evidence_ids or set(),
        existing_evidence_hashes=existing_evidence_hashes or set(),
    )
    return EconomicControlResult(
        governor=decision,
        evidence=evidence_result,
    )


def settle_verified_revenue(
    *,
    revenue_event_id: str,
    evidence_result: IntegrityResult,
    causality: CausalChain,
    existing_events: list[SettlementEvent] | None = None,
) -> LedgerSnapshot:
    """Settle only a validated proof through the deterministic ledger rebuild."""
    if not evidence_result.valid or evidence_result.proof is None:
        raise ValueError("cannot settle unverified payment evidence")

    event = SettlementEvent(
        revenue_event_id=revenue_event_id,
        proof=evidence_result.proof,
        causality=causality,
    )
    events = list(existing_events or [])
    events.append(event)
    return rebuild_ledger(events)


def validate_attribution(attribution: RevenueAttribution) -> RevenueAttribution:
    if not attribution.is_valid():
        raise ValueError("invalid revenue attribution")
    return attribution

"""Audit adapter for economic decisions and verified revenue."""

from __future__ import annotations

from .audit_ledger import AuditEvent, create_audit_event
from .economic_decision import EconomicDecision
from .revenue_gate import ConfirmedRevenue


def audit_decision(
    decision: EconomicDecision,
    *,
    occurred_at: str | None = None,
) -> AuditEvent:
    return create_audit_event(
        event_type="ECONOMIC_DECISION",
        opportunity_id=decision.opportunity_id,
        payload={
            "decision": decision.decision.value,
            "score": decision.score,
            "reasons": list(decision.reasons),
        },
        occurred_at=occurred_at,
    )


def audit_confirmed_revenue(
    revenue: ConfirmedRevenue,
    *,
    occurred_at: str | None = None,
) -> AuditEvent:
    return create_audit_event(
        event_type="CONFIRMED_REVENUE",
        opportunity_id=revenue.opportunity_id,
        payload={
            "amount": revenue.amount,
            "currency": revenue.currency,
            "evidence_id": revenue.evidence_id,
        },
        occurred_at=occurred_at,
    )

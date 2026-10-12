"""Evidence-bound revenue realization.

Payment verification alone never proves realized revenue.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import CommercialEvidenceGate, Evidence


@dataclass(frozen=True)
class RevenueVerification:
    order_id: str
    realized: bool
    payment_evidence_id: str | None
    revenue_evidence_id: str | None
    reason: str


class RevenueVerificationService:
    def __init__(self, evidence: CommercialEvidenceGate) -> None:
        self.evidence = evidence

    def verify(
        self,
        order_id: str,
        payment_evidence: Evidence | None,
        revenue_evidence: Evidence | None,
    ) -> RevenueVerification:
        if payment_evidence is None:
            return RevenueVerification(
                order_id, False, None, None, "PAYMENT_VERIFICATION_REQUIRED"
            )
        if revenue_evidence is None:
            return RevenueVerification(
                order_id, False, payment_evidence.evidence_id, None,
                "REVENUE_EVIDENCE_REQUIRED"
            )
        if payment_evidence.order_id != order_id or revenue_evidence.order_id != order_id:
            return RevenueVerification(
                order_id, False, payment_evidence.evidence_id,
                revenue_evidence.evidence_id, "REVENUE_ORDER_MISMATCH"
            )
        if not self.evidence.can_mark_revenue_realized(order_id):
            return RevenueVerification(
                order_id, False, payment_evidence.evidence_id,
                revenue_evidence.evidence_id, "REVENUE_VERIFICATION_GATE_BLOCKED"
            )
        return RevenueVerification(
            order_id, True, payment_evidence.evidence_id,
            revenue_evidence.evidence_id, "REVENUE_REALIZED"
        )

"""Commercial acquisition and delivery evidence loop.

This layer prepares and tracks customer opportunities without sending messages,
accepting contracts, charging customers, or moving funds automatically.
"""
from __future__ import annotations

from dataclasses import dataclass, field


STAGES = (
    "OFFER_DEFINED",
    "PROSPECT_IDENTIFIED",
    "CUSTOMER_VALIDATED",
    "DELIVERY_VERIFIED",
    "PAYMENT_VERIFIED",
    "REVENUE_REALIZED",
    "PROFIT_VERIFIED",
)


@dataclass(frozen=True)
class CommercialCase:
    case_id: str
    capability_id: str
    offer: str
    prospect_evidence: str | None = None
    customer_evidence: str | None = None
    delivery_evidence: str | None = None
    payment_evidence: str | None = None
    revenue_evidence: str | None = None
    cost_evidence: str | None = None
    evidence_refs: list[str] = field(default_factory=list)

    def stage(self) -> str:
        if self.revenue_evidence and self.cost_evidence:
            return "PROFIT_VERIFIED"
        if self.revenue_evidence:
            return "REVENUE_REALIZED"
        if self.payment_evidence:
            return "PAYMENT_VERIFIED"
        if self.delivery_evidence:
            return "DELIVERY_VERIFIED"
        if self.customer_evidence:
            return "CUSTOMER_VALIDATED"
        if self.prospect_evidence:
            return "PROSPECT_IDENTIFIED"
        return "OFFER_DEFINED"

    def next_evidence_required(self) -> str:
        requirements = {
            "OFFER_DEFINED": "prospect_evidence",
            "PROSPECT_IDENTIFIED": "customer_evidence",
            "CUSTOMER_VALIDATED": "delivery_evidence",
            "DELIVERY_VERIFIED": "payment_evidence",
            "PAYMENT_VERIFIED": "revenue_evidence",
            "REVENUE_REALIZED": "cost_evidence",
            "PROFIT_VERIFIED": "none",
        }
        return requirements[self.stage()]

    def to_record(self) -> dict:
        if not self.case_id.strip():
            raise ValueError("case_id required")
        if not self.capability_id.strip():
            raise ValueError("capability_id required")
        if not self.offer.strip():
            raise ValueError("offer required")
        return {
            "case_id": self.case_id,
            "capability_id": self.capability_id,
            "offer": self.offer,
            "stage": self.stage(),
            "next_evidence_required": self.next_evidence_required(),
            "evidence_refs": list(self.evidence_refs),
            "automatic_outreach": False,
            "automatic_contract": False,
            "automatic_charge": False,
            "automatic_withdrawal": False,
            "funds_moved_by_brain": False,
        }

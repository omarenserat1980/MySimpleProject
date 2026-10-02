"""Bounded commercial engine: customer signals -> offers -> opportunities -> approval."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class CustomerSignal:
    source: str
    problem: str
    evidence: list[str] = field(default_factory=list)
    customer_type: str = "unknown"

@dataclass
class Offer:
    name: str
    deliverables: list[str]
    price_note: str
    evidence_required: list[str] = field(default_factory=list)

class RevenueEngine:
    def __init__(self, offers: list[Offer]):
        self.offers = offers

    def understand_customer(self, signal: CustomerSignal) -> dict:
        return {
            "customer_type": signal.customer_type,
            "problem": signal.problem,
            "evidence": signal.evidence,
            "evidence_count": len(signal.evidence),
            "status": "QUALIFIED" if signal.problem.strip() and signal.evidence else "NEEDS_EVIDENCE",
        }

    def match_offers(self, signal: CustomerSignal) -> list[dict]:
        return [{
            "offer": o.name,
            "deliverables": o.deliverables,
            "price_note": o.price_note,
            "fit_status": "REVIEW_REQUIRED",
        } for o in self.offers]

    def create_opportunity(self, signal: CustomerSignal) -> dict:
        customer = self.understand_customer(signal)
        return {
            "status": "READY_FOR_HUMAN_REVIEW" if customer["status"] == "QUALIFIED" else "BLOCKED",
            "customer": customer,
            "offers": self.match_offers(signal),
            "external_action": "REQUIRES_AUTHORIZATION",
        }

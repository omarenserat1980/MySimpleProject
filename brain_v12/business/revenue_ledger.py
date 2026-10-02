"""Audited revenue ledger; no transaction execution."""
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class RevenueRecord:
    opportunity_id: str
    amount_note: str
    currency: str
    evidence: list[str] = field(default_factory=list)
    status: str = "PAYMENT_PENDING"

    def verify(self, evidence: str) -> dict:
        if not evidence.strip():
            raise ValueError("payment evidence required")
        self.evidence.append(evidence)
        self.status="PAYMENT_VERIFIED"
        return self.snapshot()

    def realize(self, evidence: str) -> dict:
        if self.status != "PAYMENT_VERIFIED":
            raise ValueError("payment must be verified first")
        if not evidence.strip():
            raise ValueError("realization evidence required")
        self.evidence.append(evidence)
        self.status="REVENUE_REALIZED"
        return self.snapshot()

    def snapshot(self) -> dict:
        return {"opportunity_id":self.opportunity_id,"amount_note":self.amount_note,
                "currency":self.currency,"evidence":self.evidence,"status":self.status}

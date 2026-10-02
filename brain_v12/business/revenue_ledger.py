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
        self.status = "PAYMENT_VERIFIED"
        return self.snapshot()

    def realize(self, evidence: str) -> dict:
        if self.status != "PAYMENT_VERIFIED":
            raise ValueError("payment must be verified first")
        if not evidence.strip():
            raise ValueError("realization evidence required")
        self.evidence.append(evidence)
        self.status = "REVENUE_REALIZED"
        return self.snapshot()

    def realize_from_mining_verification(self, verification: dict) -> dict:
        """Realize mining revenue only from an independently verified payout result.

        The mining verifier, not free-form ledger text, must establish the payout,
        transaction ID, and on-chain proof before this ledger can realize revenue.
        """
        if not isinstance(verification, dict):
            raise ValueError("mining verification result required")
        if verification.get("opportunity_id") != self.opportunity_id:
            raise ValueError("opportunity_id mismatch")
        if verification.get("state") != "REVENUE_REALIZED":
            raise ValueError("mining verification must be REVENUE_REALIZED")

        payout = verification.get("evidence", {}).get("payout_verification", {})
        if payout.get("status") != "VERIFIED_COMPLETED":
            raise ValueError("verified payout evidence required")
        if not payout.get("txid") or not payout.get("explorer_url"):
            raise ValueError("transaction and explorer evidence required")
        if payout.get("financial_state") != "REVENUE_REALIZED":
            raise ValueError("financial realization evidence required")

        self.evidence.append(
            f"mining:{verification['provider']}:{payout['txid']}:{payout['explorer_url']}"
        )
        self.status = "REVENUE_REALIZED"
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "amount_note": self.amount_note,
            "currency": self.currency,
            "evidence": self.evidence,
            "status": self.status,
        }

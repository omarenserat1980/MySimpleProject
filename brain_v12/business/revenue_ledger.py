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

    def verify(self, evidence: dict) -> dict:
        """Verify payment only from structured, auditable payment evidence."""
        if not isinstance(evidence, dict):
            raise ValueError("structured payment evidence required")
        transaction_id = str(evidence.get("transaction_id", "")).strip()
        evidence_ref = str(evidence.get("evidence_ref", "")).strip()
        if not transaction_id or not evidence_ref:
            raise ValueError("transaction_id and evidence_ref required")
        self.evidence.append(f"payment:{transaction_id}:{evidence_ref}")
        self.status = "PAYMENT_VERIFIED"
        return self.snapshot()

    def realize(self, evidence: dict) -> dict:
        """Recognize revenue only after verified payment plus delivery reconciliation."""
        if self.status != "PAYMENT_VERIFIED":
            raise ValueError("payment must be verified first")
        if not isinstance(evidence, dict):
            raise ValueError("structured realization evidence required")
        delivery_ref = str(evidence.get("delivery_evidence_ref", "")).strip()
        reconciliation_ref = str(evidence.get("reconciliation_ref", "")).strip()
        if not delivery_ref or not reconciliation_ref:
            raise ValueError("delivery_evidence_ref and reconciliation_ref required")
        self.evidence.append(f"realization:{delivery_ref}:{reconciliation_ref}")
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

        evidence = verification.get("evidence", {})
        payout = evidence.get("payout_verification", {})
        blockchain = evidence.get("blockchain_proof", {})
        expected_txid = str(evidence.get("payout_txid", "")).strip()
        if payout.get("status") != "VERIFIED_COMPLETED":
            raise ValueError("verified payout evidence required")
        if payout.get("financial_state") != "REVENUE_REALIZED":
            raise ValueError("financial realization evidence required")
        if not expected_txid or not blockchain.get("txid") or not blockchain.get("explorer_url"):
            raise ValueError("transaction and explorer evidence required")
        if blockchain.get("txid") != expected_txid:
            raise ValueError("blockchain proof txid mismatch")
        if str(blockchain.get("chain_status", "")).upper() != "CONFIRMED":
            raise ValueError("confirmed blockchain proof required")
        if int(blockchain.get("confirmations", 0)) < 1:
            raise ValueError("blockchain confirmations required")

        self.evidence.append(
            f"mining:{verification['provider']}:{expected_txid}:{blockchain['explorer_url']}"
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

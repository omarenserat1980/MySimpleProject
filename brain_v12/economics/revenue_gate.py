"""Evidence-backed revenue ledger primitives for Brain Economics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class PaymentEvidence:
    evidence_id: str
    opportunity_id: str
    amount: float
    currency: str
    received_at: str
    proof_ref: str

    def is_valid(self) -> bool:
        if self.amount <= 0 or not self.currency.strip():
            return False
        if not self.proof_ref.strip():
            return False
        try:
            datetime.fromisoformat(self.received_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True


@dataclass(frozen=True)
class ConfirmedRevenue:
    opportunity_id: str
    amount: float
    currency: str
    evidence_id: str
    recorded_at: str

    @classmethod
    def from_evidence(cls, evidence: PaymentEvidence) -> "ConfirmedRevenue":
        if not evidence.is_valid():
            raise ValueError("invalid payment evidence")
        return cls(
            opportunity_id=evidence.opportunity_id,
            amount=evidence.amount,
            currency=evidence.currency,
            evidence_id=evidence.evidence_id,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )

"""Evidence-bound payment verification service."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import CommercialEvidenceGate, Evidence
from .payment_guard import PaymentIdempotencyGuard, PaymentIntent


@dataclass(frozen=True)
class PaymentVerification:
    order_id: str
    provider_id: str
    verified: bool
    evidence_id: str | None
    reason: str


class EvidenceBoundPaymentService:
    def __init__(
        self,
        idempotency: PaymentIdempotencyGuard,
        evidence: CommercialEvidenceGate,
    ) -> None:
        self.idempotency = idempotency
        self.evidence = evidence

    def register_intent(self, intent: PaymentIntent) -> bool:
        return self.idempotency.register(intent)

    def verify(
        self,
        order_id: str,
        provider_id: str,
        evidence: Evidence | None,
    ) -> PaymentVerification:
        if evidence is None:
            return PaymentVerification(
                order_id, provider_id, False, None, "PAYMENT_EVIDENCE_REQUIRED"
            )
        if evidence.order_id != order_id:
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "EVIDENCE_ORDER_MISMATCH"
            )
        if not self.evidence.can_mark_payment_verified(order_id):
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "PAYMENT_VERIFICATION_GATE_BLOCKED"
            )
        return PaymentVerification(
            order_id, provider_id, True, evidence.evidence_id, "PAYMENT_VERIFIED"
        )

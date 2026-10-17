"""Evidence-bound payment verification service.

A recorded evidence row is not, by itself, proof that a payment provider
authenticated the event. Verification therefore fails closed unless a trusted
provider adapter is explicitly supplied and approves the exact recorded row.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .evidence import CommercialEvidenceGate, Evidence
from .payment_guard import PaymentIdempotencyGuard, PaymentIntent


ProviderEvidenceVerifier = Callable[[Evidence, str], bool]


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
        provider_evidence_verifier: ProviderEvidenceVerifier | None = None,
    ) -> None:
        self.idempotency = idempotency
        self.evidence = evidence
        self.provider_evidence_verifier = provider_evidence_verifier

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
        if evidence.evidence_type != "PAYMENT_VERIFICATION":
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "PAYMENT_VERIFICATION_EVIDENCE_TYPE_REQUIRED"
            )
        if (
            not isinstance(provider_id, str)
            or not provider_id.strip()
            or not isinstance(evidence.source, str)
            or evidence.source.strip().casefold() != provider_id.strip().casefold()
        ):
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "EVIDENCE_PROVIDER_MISMATCH"
            )
        recorded = self.evidence.for_order(order_id, "PAYMENT_VERIFICATION")
        if not any(row == evidence for row in recorded):
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "PAYMENT_EVIDENCE_NOT_REGISTERED"
            )
        if self.provider_evidence_verifier is None:
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "TRUSTED_PROVIDER_VERIFIER_NOT_CONFIGURED"
            )
        try:
            provider_verified = self.provider_evidence_verifier(evidence, provider_id)
        except Exception:
            provider_verified = False
        if provider_verified is not True:
            return PaymentVerification(
                order_id, provider_id, False, evidence.evidence_id,
                "TRUSTED_PROVIDER_EVIDENCE_REJECTED"
            )
        return PaymentVerification(
            order_id, provider_id, True, evidence.evidence_id, "PAYMENT_VERIFIED"
        )

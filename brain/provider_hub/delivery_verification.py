"""Evidence-bound delivery verification."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import CommercialEvidenceGate, Evidence


@dataclass(frozen=True)
class DeliveryVerification:
    order_id: str
    verified: bool
    evidence_id: str | None
    reason: str


class DeliveryVerificationService:
    def __init__(self, evidence: CommercialEvidenceGate) -> None:
        self.evidence = evidence

    def verify(self, order_id: str, evidence: Evidence | None) -> DeliveryVerification:
        if evidence is None:
            return DeliveryVerification(
                order_id, False, None, "DELIVERY_EVIDENCE_REQUIRED"
            )
        if evidence.order_id != order_id:
            return DeliveryVerification(
                order_id, False, evidence.evidence_id, "DELIVERY_ORDER_MISMATCH"
            )
        if not self.evidence.can_mark_delivery_verified(order_id):
            return DeliveryVerification(
                order_id, False, evidence.evidence_id,
                "DELIVERY_VERIFICATION_GATE_BLOCKED"
            )
        return DeliveryVerification(
            order_id, True, evidence.evidence_id, "DELIVERY_VERIFIED"
        )

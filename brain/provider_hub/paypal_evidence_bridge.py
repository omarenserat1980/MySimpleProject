"""Convert a reconciled PayPal capture into BRAIN payment evidence.

This bridge intentionally does not accept webhook payloads as capture proof.
Callers must verify webhook signatures and/or fetch the capture from PayPal,
then pass the authoritative capture response and the stored order expectations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .evidence import Evidence
from .paypal_adapter import PayPalAdapter


@dataclass(frozen=True)
class PayPalPaymentEvidence:
    evidence: Evidence
    capture_id: str


class PayPalEvidenceBridge:
    @staticmethod
    def from_capture(
        *,
        response: dict[str, Any],
        order_id: str,
        paypal_order_id: str,
        amount: str,
        currency: str,
    ) -> PayPalPaymentEvidence:
        verified = PayPalAdapter.validate_capture(
            response=response,
            expected_order_id=order_id,
            expected_paypal_order_id=paypal_order_id,
            expected_amount=amount,
            expected_currency=currency,
        )
        capture_id = verified["capture_id"]
        evidence = Evidence.create(
            evidence_id=f"paypal:capture:{capture_id}",
            evidence_type="PAYMENT_VERIFICATION",
            order_id=order_id,
            source="paypal",
            reference=capture_id,
            payload=verified,
        )
        return PayPalPaymentEvidence(evidence=evidence, capture_id=capture_id)

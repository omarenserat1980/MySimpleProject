"""Bridge verified PayTabs callbacks into BRAIN payment evidence."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import Evidence, CommercialEvidenceGate
from .paytabs_webhook import parse_and_validate_payment


@dataclass(frozen=True)
class PayTabsPaymentEvidence:
    evidence: Evidence
    transaction_ref: str


class PayTabsEvidenceBridge:
    def __init__(self, server_key: str) -> None:
        if not server_key:
            raise ValueError("PAYTABS_SERVER_KEY_MISSING")
        self.server_key = server_key

    def verify_callback(
        self,
        raw_body: bytes,
        signature: str,
        *,
        order_id: str,
        amount: str,
        currency: str,
    ) -> PayTabsPaymentEvidence:
        payload = parse_and_validate_payment(
            raw_body,
            signature,
            self.server_key,
            expected_order_id=order_id,
            expected_amount=amount,
            expected_currency=currency,
        )
        transaction_ref = str(payload["tran_ref"])
        evidence = Evidence(
            evidence_id=f"paytabs:{transaction_ref}",
            evidence_type="PAYMENT_VERIFICATION",
            order_id=order_id,
            source="paytabs",
            reference=transaction_ref,
            observed_at=str(payload.get("transaction_time", "")),
            payload=payload,
        )
        CommercialEvidenceGate().can_mark_payment_verified([evidence], order_id)
        return PayTabsPaymentEvidence(evidence=evidence, transaction_ref=transaction_ref)

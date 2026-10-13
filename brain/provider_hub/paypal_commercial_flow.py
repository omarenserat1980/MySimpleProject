"""Fail-closed PayPal commercial state coordinator.

This is a deterministic in-process gate, not durable storage. Production webhook
handlers must persist its evidence, idempotency keys, order state and ledger
entries transactionally (for example in Cloudflare D1) before acknowledging.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .commercial_ledger import CommercialLedger
from .commercial_state import CommercialOrderState
from .delivery_verification import DeliveryVerificationService
from .evidence import CommercialEvidenceGate, Evidence
from .paypal_evidence_bridge import PayPalEvidenceBridge
from .payment_guard import PaymentIdempotencyGuard, PaymentIntent


@dataclass(frozen=True)
class PayPalCommercialResult:
    order_id: str
    state: str
    evidence_id: str | None
    reason: str


class PayPalCommercialFlow:
    def __init__(self) -> None:
        self.evidence = CommercialEvidenceGate()
        self.idempotency = PaymentIdempotencyGuard()
        self.ledger = CommercialLedger()
        self._orders: dict[str, CommercialOrderState] = {}

    def register_order(self, *, order_id: str, paypal_order_id: str,
                       amount_minor: int, currency: str,
                       idempotency_key: str) -> bool:
        if not order_id or not paypal_order_id or amount_minor <= 0:
            raise ValueError("INVALID_PAYMENT_INTENT")
        currency = currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("INVALID_CURRENCY")
        accepted = self.idempotency.register(PaymentIntent(
            order_id=order_id,
            idempotency_key=idempotency_key,
            provider_id=f"paypal:{paypal_order_id}",
            amount_minor=amount_minor,
            currency=currency,
        ))
        if order_id not in self._orders:
            self._orders[order_id] = CommercialOrderState(order_id)
        return accepted

    def accept_capture(self, *, response: dict[str, Any], order_id: str,
                       paypal_order_id: str, amount: str, currency: str) -> PayPalCommercialResult:
        state = self._orders.get(order_id)
        if state is None:
            return PayPalCommercialResult(order_id, "NEW", None, "PAYMENT_INTENT_REQUIRED")
        verified = PayPalEvidenceBridge.from_capture(
            response=response, order_id=order_id,
            paypal_order_id=paypal_order_id, amount=amount, currency=currency,
        )
        evidence = verified.evidence
        if state.state != "NEW":
            # Same capture delivery is an idempotent no-op; different capture is rejected.
            existing = self.evidence.for_order(order_id, "PAYMENT_VERIFICATION")
            if any(e.evidence_id == evidence.evidence_id for e in existing):
                return PayPalCommercialResult(order_id, state.state, evidence.evidence_id, "DUPLICATE_CAPTURE_IGNORED")
            raise ValueError("ORDER_ALREADY_HAS_PAYMENT_EVIDENCE")
        self.evidence.add(evidence)
        state.transition("PAYMENT_VERIFIED", evidence_ok=True)
        self.ledger.record(
            entry_id=f"paypal:{verified.capture_id}:payment",
            order_id=order_id, from_state="NEW", to_state="PAYMENT_VERIFIED",
            evidence_refs=(evidence.evidence_id,), provider_id="paypal",
            amount_minor=int(round(float(amount) * 100)), currency=currency.upper(),
            metadata={"paypal_order_id": paypal_order_id, "capture_id": verified.capture_id},
        )
        return PayPalCommercialResult(order_id, state.state, evidence.evidence_id, "PAYMENT_VERIFIED_PENDING_DELIVERY")

    def verify_delivery(self, *, order_id: str, evidence: Evidence) -> PayPalCommercialResult:
        state = self._orders.get(order_id)
        if state is None:
            return PayPalCommercialResult(order_id, "NEW", evidence.evidence_id, "PAYMENT_INTENT_REQUIRED")
        if state.state != "PAYMENT_VERIFIED":
            raise ValueError("PAYMENT_MUST_BE_VERIFIED_BEFORE_DELIVERY")
        if evidence.evidence_type != "DELIVERY_VERIFICATION" or evidence.order_id != order_id:
            raise ValueError("DELIVERY_EVIDENCE_MISMATCH")
        self.evidence.add(evidence)
        result = DeliveryVerificationService(self.evidence).verify(order_id, evidence)
        if not result.verified:
            raise ValueError(result.reason)
        state.transition("DELIVERY_VERIFIED", evidence_ok=True)
        self.ledger.record(
            entry_id=f"delivery:{evidence.evidence_id}",
            order_id=order_id, from_state="PAYMENT_VERIFIED", to_state="DELIVERY_VERIFIED",
            evidence_refs=(evidence.evidence_id,), provider_id="paypal",
        )
        return PayPalCommercialResult(order_id, state.state, evidence.evidence_id, "DELIVERY_VERIFIED_REVENUE_PENDING")

    def realize_revenue(self, *, order_id: str, evidence: Evidence,
                        amount_minor: int, currency: str) -> PayPalCommercialResult:
        state = self._orders.get(order_id)
        if state is None or state.state != "DELIVERY_VERIFIED":
            raise ValueError("DELIVERY_VERIFICATION_REQUIRED_BEFORE_REVENUE")
        if evidence.evidence_type != "REVENUE_CONFIRMATION" or evidence.order_id != order_id:
            raise ValueError("REVENUE_EVIDENCE_MISMATCH")
        if amount_minor <= 0 or len(currency.strip()) != 3:
            raise ValueError("INVALID_REVENUE_AMOUNT_OR_CURRENCY")
        self.evidence.add(evidence)
        if not self.evidence.can_mark_delivery_verified(order_id):
            raise ValueError("DELIVERY_VERIFICATION_REQUIRED_BEFORE_REVENUE")
        state.transition("REVENUE_REALIZED", evidence_ok=True)
        payments = self.evidence.for_order(order_id, "PAYMENT_VERIFICATION")
        deliveries = self.evidence.for_order(order_id, "DELIVERY_VERIFICATION")
        self.ledger.record(
            entry_id=f"revenue:{order_id}:{evidence.evidence_id}",
            order_id=order_id, from_state="DELIVERY_VERIFIED", to_state="REVENUE_REALIZED",
            evidence_refs=(payments[0].evidence_id, deliveries[0].evidence_id, evidence.evidence_id),
            provider_id="paypal", amount_minor=amount_minor, currency=currency.upper(),
        )
        return PayPalCommercialResult(order_id, state.state, evidence.evidence_id, "REVENUE_REALIZED")

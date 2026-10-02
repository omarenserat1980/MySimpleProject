"""Evidence-first commercial governance primitives for BRAIN Cloud."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

COMMERCIAL_STATES = (
    "DISCOVERED","PRICED","QUOTED","CUSTOMER_ACCEPTED","CONTRACTED",
    "INVOICED","PAYMENT_PENDING","PAYMENT_VERIFIED","DELIVERED","REVENUE_REALIZED",
)

PAYMENT_TERMINAL = {"FAILED","REVERSED","REFUNDED","DISPUTED"}

@dataclass(frozen=True)
class PriceInput:
    direct_cost: Decimal
    operating_cost: Decimal = Decimal("0")
    payment_cost: Decimal = Decimal("0")
    risk_reserve: Decimal = Decimal("0")
    mandatory_costs: Decimal = Decimal("0")
    target_margin: Decimal = Decimal("0")

    def floor(self) -> Decimal:
        return sum((self.direct_cost, self.operating_cost, self.payment_cost,
                    self.risk_reserve, self.mandatory_costs), Decimal("0"))

    def target_price(self) -> Decimal:
        base = self.floor()
        if self.target_margin < 0 or self.target_margin >= 1:
            raise ValueError("target_margin must be >= 0 and < 1")
        return (base / (Decimal("1") - self.target_margin)).quantize(Decimal("0.01"))

def validate_price(price: Decimal, inputs: PriceInput, *, human_approval: bool = False) -> None:
    if price < inputs.floor() and not human_approval:
        raise ValueError("price is below the approved price floor")
    if price <= 0:
        raise ValueError("price must be positive")

def validate_promotion(*, reference_price: Decimal, promotional_price: Decimal,
                       start_date: str, end_date: str, eligibility: str,
                       approval: bool) -> None:
    if reference_price <= 0 or promotional_price <= 0:
        raise ValueError("promotion prices must be positive")
    if promotional_price > reference_price:
        raise ValueError("promotional price cannot exceed reference price")
    if not start_date or not end_date or not eligibility:
        raise ValueError("promotion dates and eligibility are required")
    if not approval:
        raise ValueError("promotion approval is required")

def verify_payment(*, invoice_id: str, amount: Decimal, currency: str,
                   transaction_id: str, evidence_ref: str) -> None:
    if not invoice_id or amount <= 0 or not currency or not transaction_id or not evidence_ref:
        raise ValueError("payment verification requires invoice, amount, currency, transaction and evidence")

def recognize_revenue(*, payment_verified: bool, delivered: bool,
                      evidence_ref: str) -> None:
    if not payment_verified:
        raise ValueError("revenue cannot be realized before payment verification")
    if not delivered:
        raise ValueError("revenue cannot be realized before delivery")
    if not evidence_ref:
        raise ValueError("revenue realization requires audit evidence")

def consent_allows(*, purpose: str, consents: Mapping[str, bool]) -> bool:
    return bool(consents.get(purpose.upper(), False))

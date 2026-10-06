"""Evidence-gated commercial control plane with cryptographic evidence binding."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from hashlib import sha256
from typing import FrozenSet


class CommercialState(str, Enum):
    PROSPECT = "PROSPECT"
    OFFER_PREPARED = "OFFER_PREPARED"
    CUSTOMER_VALIDATED = "CUSTOMER_VALIDATED"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    DELIVERY_VERIFIED = "DELIVERY_VERIFIED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    REVENUE_REALIZED = "REVENUE_REALIZED"
    PROFIT_VERIFIED = "PROFIT_VERIFIED"
    CLOSED = "CLOSED"


REQUIRED_EVIDENCE: dict[CommercialState, FrozenSet[str]] = {
    CommercialState.OFFER_PREPARED: frozenset({"offer"}),
    CommercialState.CUSTOMER_VALIDATED: frozenset({"offer", "customer_acceptance"}),
    CommercialState.ORDER_ACCEPTED: frozenset({"offer", "customer_acceptance", "order"}),
    CommercialState.DELIVERY_VERIFIED: frozenset({"offer", "customer_acceptance", "order", "delivery"}),
    CommercialState.PAYMENT_VERIFIED: frozenset({"offer", "customer_acceptance", "order", "delivery", "payment"}),
    CommercialState.REVENUE_REALIZED: frozenset({"offer", "customer_acceptance", "order", "delivery", "payment"}),
    CommercialState.PROFIT_VERIFIED: frozenset({"offer", "customer_acceptance", "order", "delivery", "payment", "cost", "reconciliation"}),
}

ALLOWED_PROVENANCE = frozenset({
    "CUSTOMER_ACCEPTANCE", "ORDER_RECORD", "DELIVERY_RECORD",
    "PAYMENT_RECEIPT", "COST_RECORD", "RECONCILIATION", "OFFER_RECORD",
})


def _money_equal(left: float | Decimal | None, right: float | Decimal | None) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


@dataclass(frozen=True)
class CommercialEvidence:
    evidence_type: str
    reference: str
    verified: bool = False
    provenance: str = ""
    client_id: str = ""
    order_id: str = ""
    amount: float | Decimal | None = None
    currency: str = ""
    source_digest: str = ""
    verified_at_utc: str = ""

    def canonical_payload(self) -> str:
        amount = "" if self.amount is None else str(Decimal(str(self.amount)))
        return "|".join((
            self.evidence_type.strip(),
            self.reference.strip(),
            self.provenance.strip(),
            self.client_id.strip(),
            self.order_id.strip(),
            amount,
            self.currency.strip().upper(),
            self.verified_at_utc.strip(),
        ))

    def calculated_source_digest(self) -> str:
        return sha256(self.canonical_payload().encode("utf-8")).hexdigest()

    def integrity_supported(self) -> bool:
        supplied = self.source_digest.strip().lower()
        return (
            len(supplied) == 64
            and all(c in "0123456789abcdef" for c in supplied)
            and bool(self.verified_at_utc.strip())
            and supplied == self.calculated_source_digest()
        )

    def independently_supported(self) -> bool:
        return (
            self.verified
            and bool(self.reference.strip())
            and self.provenance in ALLOWED_PROVENANCE
            and self.integrity_supported()
        )


@dataclass
class CommercialCase:
    client_id: str
    state: CommercialState = CommercialState.PROSPECT
    evidence: list[CommercialEvidence] = field(default_factory=list)
    expected_order_id: str = ""
    expected_amount: float | Decimal | None = None
    expected_currency: str = ""

    def verified_types(self) -> set[str]:
        return {
            item.evidence_type
            for item in self.evidence
            if self.evidence_matches_case(item) and item.independently_supported()
        }

    def evidence_matches_case(self, item: CommercialEvidence) -> bool:
        sensitive = item.evidence_type in {"payment", "order", "delivery", "customer_acceptance"}
        if sensitive:
            if not item.client_id or item.client_id != self.client_id:
                return False
            if not item.order_id or not self.expected_order_id or item.order_id != self.expected_order_id:
                return False
            if item.amount is None or self.expected_amount is None or not _money_equal(item.amount, self.expected_amount):
                return False
            if not item.currency or not self.expected_currency or item.currency.upper() != self.expected_currency.upper():
                return False
        else:
            if item.client_id and item.client_id != self.client_id:
                return False
            if item.order_id and self.expected_order_id and item.order_id != self.expected_order_id:
                return False
            if item.amount is not None and self.expected_amount is not None and not _money_equal(item.amount, self.expected_amount):
                return False
            if item.currency and self.expected_currency and item.currency.upper() != self.expected_currency.upper():
                return False
        return True

    def can_enter(self, target: CommercialState) -> bool:
        return REQUIRED_EVIDENCE.get(target, frozenset()).issubset(self.verified_types())

    def state_integrity_ok(self) -> bool:
        return REQUIRED_EVIDENCE.get(self.state, frozenset()).issubset(self.verified_types())

    def transition(self, target: CommercialState) -> None:
        if not self.can_enter(target):
            missing = sorted(REQUIRED_EVIDENCE.get(target, frozenset()) - self.verified_types())
            raise ValueError(f"Transition blocked; missing evidence: {missing}")
        self.state = target


def revenue_claim_allowed(case: CommercialCase) -> bool:
    return case.state == CommercialState.REVENUE_REALIZED and case.state_integrity_ok()


def profit_claim_allowed(case: CommercialCase) -> bool:
    return case.state == CommercialState.PROFIT_VERIFIED and case.state_integrity_ok()


def forbidden_financial_side_effect(action: str) -> bool:
    return action in {"auto_contract", "auto_charge", "auto_purchase", "auto_withdrawal", "auto_transfer"}

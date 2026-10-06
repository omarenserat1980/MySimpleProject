"""Evidence-gated commercial control plane with strict identity, money, source and chronology integrity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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

_EVIDENCE_ORDER = {
    "offer": 0,
    "customer_acceptance": 1,
    "order": 2,
    "delivery": 3,
    "payment": 4,
}


def _money_equal(left: float | Decimal | None, right: float | Decimal | None) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except (InvalidOperation, ValueError):
        return False


def _parse_time(value: str) -> datetime | None:
    if not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _valid_verification_time(value: str) -> bool:
    parsed = _parse_time(value)
    return parsed is not None and parsed <= datetime.now(timezone.utc)


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
    event_at_utc: str = ""

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
            self.event_at_utc.strip(),
            self.verified_at_utc.strip(),
        ))

    def calculated_source_digest(self) -> str:
        return sha256(self.canonical_payload().encode("utf-8")).hexdigest()

    def integrity_supported(self) -> bool:
        supplied = self.source_digest.strip().lower()
        event_time = _parse_time(self.event_at_utc)
        verification_time = _parse_time(self.verified_at_utc)
        return (
            len(supplied) == 64
            and all(c in "0123456789abcdef" for c in supplied)
            and event_time is not None
            and verification_time is not None
            and verification_time <= datetime.now(timezone.utc)
            and event_time <= verification_time
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

    def duplicate_references(self) -> set[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item in self.evidence:
            reference = item.reference.strip()
            if not reference:
                continue
            if reference in seen:
                duplicates.add(reference)
            seen.add(reference)
        return duplicates

    def duplicate_evidence_types(self) -> set[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item in self.evidence:
            evidence_type = item.evidence_type.strip()
            if not evidence_type:
                continue
            if evidence_type in seen:
                duplicates.add(evidence_type)
            seen.add(evidence_type)
        return duplicates

    def duplicate_source_digests(self) -> set[str]:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for item in self.evidence:
            digest = item.source_digest.strip().lower()
            if not digest:
                continue
            if digest in seen:
                duplicates.add(digest)
            seen.add(digest)
        return duplicates

    def evidence_set_integrity_ok(self) -> bool:
        return (
            not self.duplicate_references()
            and not self.duplicate_source_digests()
            and not self.duplicate_evidence_types()
        )

    def chronology_integrity_ok(self) -> bool:
        by_type: dict[str, CommercialEvidence] = {}
        for item in self.evidence:
            if item.evidence_type in _EVIDENCE_ORDER:
                if item.evidence_type in by_type:
                    return False
                if _parse_time(item.event_at_utc) is None:
                    return False
                by_type[item.evidence_type] = item

        ordered = sorted(by_type.items(), key=lambda pair: _EVIDENCE_ORDER[pair[0]])
        previous_time: datetime | None = None
        for _, item in ordered:
            current_time = _parse_time(item.event_at_utc)
            if current_time is None:
                return False
            if previous_time is not None and current_time < previous_time:
                return False
            previous_time = current_time
        return True

    def verified_types(self) -> set[str]:
        if not self.evidence_set_integrity_ok() or not self.chronology_integrity_ok():
            return set()
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
        return (
            self.evidence_set_integrity_ok()
            and self.chronology_integrity_ok()
            and REQUIRED_EVIDENCE.get(self.state, frozenset()).issubset(self.verified_types())
        )

    def transition(self, target: CommercialState) -> None:
        if target == self.state:
            return
        if target == CommercialState.PROSPECT:
            raise ValueError("Commercial state cannot move backward to PROSPECT.")
        state_order = list(CommercialState)
        if self.state in state_order and target in state_order:
            if state_order.index(target) < state_order.index(self.state):
                raise ValueError(f"Commercial state cannot move backward: {self.state.value} -> {target.value}")
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

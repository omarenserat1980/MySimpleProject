"""Evidence-gated commercial control plane with provenance checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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
    "CUSTOMER_ACCEPTANCE",
    "ORDER_RECORD",
    "DELIVERY_RECORD",
    "PAYMENT_RECEIPT",
    "COST_RECORD",
    "RECONCILIATION",
    "OFFER_RECORD",
})


@dataclass(frozen=True)
class CommercialEvidence:
    evidence_type: str
    reference: str
    verified: bool = False
    provenance: str = ""

    def independently_supported(self) -> bool:
        return (
            self.verified
            and bool(self.reference.strip())
            and self.provenance in ALLOWED_PROVENANCE
        )


@dataclass
class CommercialCase:
    client_id: str
    state: CommercialState = CommercialState.PROSPECT
    evidence: list[CommercialEvidence] = field(default_factory=list)

    def verified_types(self) -> set[str]:
        return {
            item.evidence_type
            for item in self.evidence
            if item.independently_supported()
        }

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

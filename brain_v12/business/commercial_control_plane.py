"""Evidence-gated commercial control plane.

This module models commercial progress; it does not execute contracts,
payments, purchases, withdrawals, or financial transfers.
"""

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
    CommercialState.ORDER_ACCEPTED: frozenset(
        {"offer", "customer_acceptance", "order"}
    ),
    CommercialState.DELIVERY_VERIFIED: frozenset(
        {"offer", "customer_acceptance", "order", "delivery"}
    ),
    CommercialState.PAYMENT_VERIFIED: frozenset(
        {"offer", "customer_acceptance", "order", "delivery", "payment"}
    ),
    CommercialState.REVENUE_REALIZED: frozenset(
        {"offer", "customer_acceptance", "order", "delivery", "payment"}
    ),
    CommercialState.PROFIT_VERIFIED: frozenset(
        {
            "offer",
            "customer_acceptance",
            "order",
            "delivery",
            "payment",
            "cost",
            "reconciliation",
        }
    ),
}


@dataclass(frozen=True)
class CommercialEvidence:
    evidence_type: str
    reference: str
    verified: bool = False


@dataclass
class CommercialCase:
    client_id: str
    state: CommercialState = CommercialState.PROSPECT
    evidence: list[CommercialEvidence] = field(default_factory=list)

    def verified_types(self) -> set[str]:
        return {
            item.evidence_type
            for item in self.evidence
            if item.verified and item.reference.strip()
        }

    def can_enter(self, target: CommercialState) -> bool:
        required = REQUIRED_EVIDENCE.get(target, frozenset())
        return required.issubset(self.verified_types())

    def transition(self, target: CommercialState) -> None:
        if target == CommercialState.REVENUE_REALIZED:
            if not self.can_enter(CommercialState.PAYMENT_VERIFIED):
                raise ValueError(
                    "REVENUE_REALIZED blocked: independently verified payment "
                    "and delivery evidence are required."
                )

        if target == CommercialState.PROFIT_VERIFIED:
            if not self.can_enter(CommercialState.PROFIT_VERIFIED):
                raise ValueError(
                    "PROFIT_VERIFIED blocked: payment, delivery, cost and "
                    "reconciliation evidence are required."
                )

        if not self.can_enter(target):
            missing = sorted(REQUIRED_EVIDENCE.get(target, frozenset()) - self.verified_types())
            raise ValueError(f"Transition blocked; missing evidence: {missing}")

        self.state = target


def revenue_claim_allowed(case: CommercialCase) -> bool:
    return case.state == CommercialState.REVENUE_REALIZED


def profit_claim_allowed(case: CommercialCase) -> bool:
    return case.state == CommercialState.PROFIT_VERIFIED


def forbidden_financial_side_effect(action: str) -> bool:
    blocked = {
        "auto_contract",
        "auto_charge",
        "auto_purchase",
        "auto_withdrawal",
        "auto_transfer",
    }
    return action in blocked

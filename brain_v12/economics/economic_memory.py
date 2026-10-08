"""Evidence-backed economic memory; never creates revenue claims."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    REJECTED = "REJECTED"
    ACCEPTED = "ACCEPTED"
    DELIVERED = "DELIVERED"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"


@dataclass(frozen=True)
class EconomicObservation:
    opportunity_class: str
    outcome: Outcome
    hours_spent: float
    advertised_pay: float
    payment_amount: float = 0.0
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.opportunity_class.strip():
            raise ValueError("opportunity_class cannot be empty")
        if self.hours_spent < 0 or self.advertised_pay < 0 or self.payment_amount < 0:
            raise ValueError("economic values cannot be negative")
        if self.outcome is Outcome.PAYMENT_VERIFIED and (
            self.payment_amount <= 0 or not self.evidence_ref
        ):
            raise ValueError("verified payment requires amount and evidence")


@dataclass(frozen=True)
class EconomicEstimate:
    opportunity_class: str
    acceptance_probability: float
    risk: float
    observations: int


def estimate(
    observations: list[EconomicObservation], opportunity_class: str
) -> EconomicEstimate:
    """Estimate only from observed outcomes; no observation means neutral priors."""
    items = [o for o in observations if o.opportunity_class == opportunity_class]
    if not items:
        return EconomicEstimate(opportunity_class, 0.5, 0.5, 0)

    accepted = sum(
        o.outcome in {
            Outcome.ACCEPTED,
            Outcome.DELIVERED,
            Outcome.PAYMENT_VERIFIED,
        }
        for o in items
    )
    rejected = sum(o.outcome is Outcome.REJECTED for o in items)

    return EconomicEstimate(
        opportunity_class=opportunity_class,
        acceptance_probability=accepted / len(items),
        risk=rejected / len(items),
        observations=len(items),
    )


def verified_payment_total(observations: list[EconomicObservation]) -> float:
    """Only observations with explicit payment evidence contribute."""
    return sum(
        o.payment_amount
        for o in observations
        if o.outcome is Outcome.PAYMENT_VERIFIED and o.evidence_ref
    )

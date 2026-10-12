"""Evidence-backed economic memory and conservative learning updates."""

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
    """Estimate from observed outcomes with a neutral prior."""
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


def conservative_update(
    prior_probability: float,
    observed_successes: int,
    observed_trials: int,
    *,
    prior_strength: int = 4,
) -> float:
    """Bayesian-style shrinkage toward the prior for small samples."""
    if not 0 <= prior_probability <= 1:
        raise ValueError("prior_probability must be between 0 and 1")
    if observed_successes < 0 or observed_trials < 0:
        raise ValueError("observations cannot be negative")
    if observed_successes > observed_trials:
        raise ValueError("successes cannot exceed trials")
    if prior_strength <= 0:
        raise ValueError("prior_strength must be positive")
    return (
        prior_probability * prior_strength + observed_successes
    ) / (prior_strength + observed_trials)


def learned_estimate(
    observations: list[EconomicObservation],
    opportunity_class: str,
    *,
    prior_probability: float = 0.5,
    prior_risk: float = 0.5,
) -> EconomicEstimate:
    """Learn conservatively so one or two outcomes cannot dominate the model."""
    items = [o for o in observations if o.opportunity_class == opportunity_class]
    if not items:
        return EconomicEstimate(opportunity_class, prior_probability, prior_risk, 0)

    successes = sum(
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
        acceptance_probability=conservative_update(
            prior_probability, successes, len(items)
        ),
        risk=conservative_update(
            prior_risk, rejected, len(items)
        ),
        observations=len(items),
    )


def verified_payment_total(observations: list[EconomicObservation]) -> float:
    """Only observations with explicit payment evidence contribute."""
    return sum(
        o.payment_amount
        for o in observations
        if o.outcome is Outcome.PAYMENT_VERIFIED and o.evidence_ref
    )

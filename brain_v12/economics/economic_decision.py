"""Explainable economic decision gate for Brain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .economic_memory import EconomicEstimate
from .opportunity_engine import Opportunity
from .opportunity_verifier import VerificationResult


class Decision(str, Enum):
    PROCEED = "PROCEED"
    HOLD = "HOLD"
    REJECT = "REJECT"


@dataclass(frozen=True)
class EconomicDecision:
    opportunity_id: str
    decision: Decision
    score: float
    reasons: tuple[str, ...]


def decide(
    opportunity: Opportunity,
    score: float,
    verification: VerificationResult,
    memory: EconomicEstimate,
    *,
    minimum_score: float = 1.0,
    minimum_confidence: float = 0.75,
) -> EconomicDecision:
    """Fail closed: unverified opportunities cannot proceed."""
    reasons: list[str] = []

    if not verification.eligible:
        return EconomicDecision(
            opportunity.opportunity_id,
            Decision.REJECT,
            score,
            tuple(verification.reasons),
        )

    if verification.confidence < minimum_confidence:
        reasons.append("verification_confidence_below_threshold")

    if score < minimum_score:
        reasons.append("economic_score_below_threshold")

    if memory.observations == 0:
        reasons.append("no_historical_evidence")

    if reasons:
        return EconomicDecision(
            opportunity.opportunity_id,
            Decision.HOLD,
            score,
            tuple(reasons),
        )

    return EconomicDecision(
        opportunity.opportunity_id,
        Decision.PROCEED,
        score,
        (),
    )

"""Single-path economic orchestrator; no parallel workers or side effects."""

from __future__ import annotations

from dataclasses import dataclass

from .economic_decision import EconomicDecision, decide
from .economic_memory import EconomicEstimate, EconomicObservation, learned_estimate
from .opportunity_engine import Opportunity, deduplicate_opportunities, rank_opportunities
from .opportunity_verifier import VerificationResult, verify_opportunity


@dataclass(frozen=True)
class OrchestrationResult:
    opportunity: Opportunity
    verification: VerificationResult
    score: float
    memory: EconomicEstimate
    decision: EconomicDecision


def evaluate(
    opportunity: Opportunity,
    *,
    opportunity_class: str,
    eligibility: list[str],
    upfront_cost_usd: float,
    source_url: str,
    last_verified_at: str,
    observations: list[EconomicObservation],
    region: str = "Jordan",
) -> OrchestrationResult:
    """Run one deterministic economic path from discovery to decision."""
    if not opportunity_class.strip():
        raise ValueError("opportunity_class cannot be empty")

    unique = deduplicate_opportunities([opportunity])
    if len(unique) != 1:
        raise ValueError("opportunity deduplication failed")

    ranked = rank_opportunities(unique)
    normalized, score_value = ranked[0]

    verification = verify_opportunity(
        opportunity_id=normalized.opportunity_id,
        eligibility=eligibility,
        upfront_cost_usd=upfront_cost_usd,
        source_url=source_url,
        last_verified_at=last_verified_at,
        region=region,
    )
    memory = learned_estimate(observations, opportunity_class)
    decision = decide(normalized, score_value, verification, memory)

    return OrchestrationResult(
        opportunity=normalized,
        verification=verification,
        score=score_value,
        memory=memory,
        decision=decision,
    )

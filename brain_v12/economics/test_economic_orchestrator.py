from datetime import datetime, timezone

from economics.economic_decision import Decision
from economics.economic_memory import EconomicEstimate, EconomicObservation, Outcome
from economics.economic_orchestrator import evaluate
from economics.opportunity_engine import Opportunity


def test_orchestrator_holds_new_class():
    result = evaluate(
        Opportunity("x", 100, .8, .8, 2, .1, .1),
        opportunity_class="new_class",
        eligibility=["Jordan", "remote"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=datetime.now(timezone.utc).isoformat(),
        observations=[],
    )
    assert result.verification.eligible
    assert result.decision.decision is Decision.HOLD
    assert "no_historical_evidence" in result.decision.reasons


def test_orchestrator_uses_class_memory():
    observations = [
        EconomicObservation("arabic_ai_evaluation", Outcome.ACCEPTED, 1, 20),
        EconomicObservation("arabic_ai_evaluation", Outcome.ACCEPTED, 1, 20),
        EconomicObservation("arabic_ai_evaluation", Outcome.REJECTED, 1, 20),
        EconomicObservation("other", Outcome.REJECTED, 1, 20),
    ]
    result = evaluate(
        Opportunity("x", 100, .8, .8, 2, .1, .1),
        opportunity_class="arabic_ai_evaluation",
        eligibility=["Jordan"],
        upfront_cost_usd=0,
        source_url="https://example.com/job",
        last_verified_at=datetime.now(timezone.utc).isoformat(),
        observations=observations,
    )
    assert result.memory.observations == 3
    assert result.memory.acceptance_probability > 0.5

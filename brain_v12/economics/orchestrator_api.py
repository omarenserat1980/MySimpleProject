"""Read-only API for the single-path economic orchestrator."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .economic_memory import EconomicObservation, Outcome
from .economic_orchestrator import evaluate
from .opportunity_engine import Opportunity, OpportunityState

router = APIRouter(
    prefix="/api/economics/orchestrator",
    tags=["economics-orchestrator"],
)


class ObservationInput(BaseModel):
    opportunity_class: str
    outcome: Outcome
    hours_spent: float = Field(ge=0)
    advertised_pay: float = Field(ge=0)
    payment_amount: float = Field(default=0, ge=0)
    evidence_ref: str | None = None


class EvaluateInput(BaseModel):
    opportunity_id: str
    opportunity_class: str
    expected_pay: float = Field(ge=0)
    acceptance_probability: float = Field(ge=0, le=1)
    brain_assistance: float = Field(ge=0, le=1)
    time_hours: float = Field(ge=0)
    entry_friction: float = Field(ge=0, le=1)
    risk: float = Field(ge=0, le=1)
    eligibility: list[str]
    upfront_cost_usd: float = Field(ge=0)
    source_url: str
    last_verified_at: str
    observations: list[ObservationInput] = []


@router.post("/evaluate")
def evaluate_opportunity(item: EvaluateInput):
    try:
        datetime.fromisoformat(item.last_verified_at.replace("Z", "+00:00"))
        observations = [
            EconomicObservation(**observation.model_dump())
            for observation in item.observations
        ]
        result = evaluate(
            Opportunity(
                opportunity_id=item.opportunity_id,
                expected_pay=item.expected_pay,
                acceptance_probability=item.acceptance_probability,
                brain_assistance=item.brain_assistance,
                time_hours=item.time_hours,
                entry_friction=item.entry_friction,
                risk=item.risk,
                state=OpportunityState.DISCOVERED,
            ),
            opportunity_class=item.opportunity_class,
            eligibility=item.eligibility,
            upfront_cost_usd=item.upfront_cost_usd,
            source_url=item.source_url,
            last_verified_at=item.last_verified_at,
            observations=observations,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "opportunity_id": result.opportunity.opportunity_id,
        "decision": result.decision.decision.value,
        "score": result.score,
        "verification": {
            "eligible": result.verification.eligible,
            "confidence": result.verification.confidence,
            "reasons": result.verification.reasons,
            "source_fingerprint": result.verification.source_fingerprint,
        },
        "memory": {
            "opportunity_class": result.memory.opportunity_class,
            "acceptance_probability": result.memory.acceptance_probability,
            "risk": result.memory.risk,
            "observations": result.memory.observations,
        },
        "reasons": result.decision.reasons,
        "side_effects": False,
    }

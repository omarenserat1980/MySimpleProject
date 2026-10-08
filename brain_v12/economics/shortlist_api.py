"""Read-only economic shortlist API."""

from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .economic_memory import EconomicObservation, Outcome
from .opportunity_factory import build_shortlist

router = APIRouter(
    prefix="/api/economics/shortlist",
    tags=["economics-shortlist"],
)


class ShortlistObservation(BaseModel):
    opportunity_class: str
    outcome: Outcome
    hours_spent: float = Field(ge=0)
    advertised_pay: float = Field(ge=0)
    payment_amount: float = Field(default=0, ge=0)
    evidence_ref: str | None = None


class ShortlistRequest(BaseModel):
    records: list[dict]
    observations: list[ShortlistObservation] = []
    max_age_days: int = Field(default=30, ge=0)
    now: str | None = None


@router.post("")
def shortlist(item: ShortlistRequest):
    observations = [
        EconomicObservation(**observation.model_dump())
        for observation in item.observations
    ]
    now = None
    if item.now:
        now = datetime.fromisoformat(item.now.replace("Z", "+00:00"))

    result = build_shortlist(
        item.records,
        observations=observations,
        max_age_days=item.max_age_days,
        now=now,
    )
    return {
        "count": len(result),
        "items": [
            {
                "opportunity_id": item.opportunity_id,
                "opportunity_class": item.opportunity_class,
                "source_fingerprint": item.source_fingerprint,
                "decision": item.decision.decision.value,
                "score": item.decision.score,
                "reasons": item.decision.reasons,
                "verification": {
                    "eligible": item.verification.eligible,
                    "confidence": item.verification.confidence,
                    "reasons": item.verification.reasons,
                },
            }
            for item in result
        ],
        "side_effects": False,
        "revenue_claimed": False,
    }

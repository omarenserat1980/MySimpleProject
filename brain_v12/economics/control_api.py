"""Read-only HTTP boundary for the unified economic control plane."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .economic_control import CausalChain, EconomicBudget
from .economic_control_plane import evaluate_control
from .economic_governor import EconomicSignal
from .revenue_gate import PaymentEvidence

router = APIRouter(
    prefix="/api/economics/control",
    tags=["economics-control"],
)


class ControlInput(BaseModel):
    opportunity_id: str
    evidence_id: str
    amount: float = Field(gt=0)
    currency: str
    received_at: str
    proof_ref: str

    verified: bool
    expected_value: float = Field(ge=0)
    execution_cost: float = Field(ge=0)
    risk_score: float = Field(ge=0, le=1)

    time_budget_hours: float = Field(ge=0)
    retry_budget: int = Field(ge=0)
    risk_budget: float = Field(ge=0, le=1)

    existing_evidence_ids: list[str] = []
    existing_evidence_hashes: list[str] = []


@router.post("/evaluate")
def evaluate_control_path(item: ControlInput):
    try:
        result = evaluate_control(
            signal=EconomicSignal(
                verified=item.verified,
                expected_value=item.expected_value,
                execution_cost=item.execution_cost,
                risk_score=item.risk_score,
            ),
            budget=EconomicBudget(
                time_hours=item.time_budget_hours,
                retry_count=item.retry_budget,
                risk_score=item.risk_budget,
            ),
            evidence=PaymentEvidence(
                evidence_id=item.evidence_id,
                opportunity_id=item.opportunity_id,
                amount=item.amount,
                currency=item.currency,
                received_at=item.received_at,
                proof_ref=item.proof_ref,
            ),
            existing_evidence_ids=set(item.existing_evidence_ids),
            existing_evidence_hashes=set(item.existing_evidence_hashes),
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return {
        "governor": {
            "action": result.governor.action.value,
            "reason": result.governor.reason,
        },
        "evidence": {
            "valid": result.evidence.valid,
            "reason": result.evidence.reason,
            "evidence_hash": (
                result.evidence.proof.evidence_hash
                if result.evidence.proof
                else None
            ),
        },
        "revenue_claimed": False,
        "side_effects": False,
    }

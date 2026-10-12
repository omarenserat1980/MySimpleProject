"""Minimal FastAPI integration for the Brain Money Opportunity Engine.

This router exposes deterministic scoring and payment-evidence shape validation.
It does not independently verify a payment, settle revenue, perform external
applications, or move money.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .opportunity_engine import Opportunity, score
from .revenue_gate import PaymentEvidence

router = APIRouter(prefix="/api/economics", tags=["economics"])


class OpportunityInput(BaseModel):
    opportunity_id: str
    expected_pay: float = Field(ge=0)
    acceptance_probability: float = Field(ge=0, le=1)
    brain_assistance: float = Field(ge=0, le=1)
    time_hours: float = Field(ge=0)
    entry_friction: float = Field(ge=0, le=1)
    risk: float = Field(ge=0, le=1)


class PaymentInput(BaseModel):
    evidence_id: str
    opportunity_id: str
    amount: float = Field(gt=0)
    currency: str
    received_at: str
    proof_ref: str


@router.post("/score")
def score_opportunity(item: OpportunityInput):
    try:
        value = score(Opportunity(**item.dict()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"opportunity_id": item.opportunity_id, "score": value}


@router.post("/revenue/verify")
def verify_payment(item: PaymentInput):
    """Validate evidence shape only; never represent this as payment verification."""
    evidence = PaymentEvidence(**item.dict())
    if (
        not evidence.evidence_id.strip()
        or not evidence.opportunity_id.strip()
        or not evidence.is_valid()
    ):
        raise HTTPException(status_code=422, detail="invalid payment evidence")

    return {
        "status": "EVIDENCE_FORMAT_VALIDATED_NOT_PAYMENT_VERIFIED",
        "evidence_id": evidence.evidence_id,
        "opportunity_id": evidence.opportunity_id,
        "revenue_claimed": False,
        "side_effects": False,
        "verification_scope": (
            "format checks only; no independent bank, payment-provider, or "
            "blockchain verification was performed"
        ),
    }

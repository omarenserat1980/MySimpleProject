"""Minimal FastAPI integration for the Brain Money Opportunity Engine.

This router exposes deterministic scoring and revenue-evidence validation.
It does not perform external applications or payments.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .opportunity_engine import Opportunity, OpportunityState, score
from .revenue_gate import ConfirmedRevenue, PaymentEvidence

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
        value = score(Opportunity(**item.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"opportunity_id": item.opportunity_id, "score": value}


@router.post("/revenue/verify")
def verify_payment(item: PaymentInput):
    evidence = PaymentEvidence(**item.model_dump())
    if not evidence.is_valid():
        raise HTTPException(status_code=422, detail="invalid payment evidence")
    revenue = ConfirmedRevenue.from_evidence(evidence)
    return {"status": "PAYMENT_VERIFIED", "revenue": revenue.__dict__}

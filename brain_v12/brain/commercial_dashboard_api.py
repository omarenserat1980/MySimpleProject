"""Commercial operations API with durable case tracking.

Evidence references remain UNVERIFIED metadata and cannot advance commercial stages.
No outreach, contracting, charging, withdrawal, or funds movement is performed.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from brain_v12.business.commercial_case import CommercialCase
from brain_v12.business.commercial_case_store import CommercialCaseStore
from brain_v12.business.commercial_operations_dashboard import build_commercial_operations_dashboard
from brain_v12.business.initial_monetization_catalog import INITIAL_MONETIZATION_CATALOG
from .control_auth import require_control_key


class CreateCommercialCase(BaseModel):
    capability_id: str = Field(min_length=1, max_length=120)
    case_id: str | None = Field(default=None, min_length=1, max_length=120)


class AddEvidenceReference(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=32)
    evidence_ref: str = Field(min_length=1, max_length=1000)


def _record(case: CommercialCase) -> dict:
    data = case.to_record()
    data.update({
        "prospect_evidence": case.prospect_evidence,
        "customer_evidence": case.customer_evidence,
        "delivery_evidence": case.delivery_evidence,
        "payment_evidence": case.payment_evidence,
        "revenue_evidence": case.revenue_evidence,
        "cost_evidence": case.cost_evidence,
    })
    return data


def router() -> APIRouter:
    api = APIRouter(prefix="/api/commercial", tags=["commercial"])

    @api.get("/dashboard")
    def dashboard() -> dict:
        store = CommercialCaseStore()
        result = build_commercial_operations_dashboard(INITIAL_MONETIZATION_CATALOG, store.list_cases())
        return {"ok": True, **result.to_record()}

    @api.get("/offers")
    def offers() -> dict:
        return {
            "ok": True,
            "offers": [
                {
                    "capability_id": x.capability_id,
                    "capability_name": x.capability_name,
                    "offer": x.offer,
                    "target_customer": x.target_customer,
                    "acquisition_channel": x.acquisition_channel,
                    "delivery_evidence": x.delivery_evidence,
                    "cost_model": x.cost_model,
                    "status": x.status,
                }
                for x in INITIAL_MONETIZATION_CATALOG
            ],
        }

    @api.get("/cases")
    def cases(request: Request) -> dict:
        require_control_key(request)
        return {"ok": True, "cases": [_record(x) for x in CommercialCaseStore().list_cases()]}

    @api.post("/cases")
    def create_case(request: Request, payload: CreateCommercialCase) -> dict:
        require_control_key(request)
        offer = next((x for x in INITIAL_MONETIZATION_CATALOG if x.capability_id == payload.capability_id), None)
        if offer is None:
            raise HTTPException(status_code=404, detail="UNKNOWN_CAPABILITY")
        case_id = (payload.case_id or "").strip() or f"case-{uuid4().hex[:12]}"
        case = CommercialCase(case_id=case_id, capability_id=offer.capability_id, offer=offer.offer)
        try:
            CommercialCaseStore().create_case(case)
        except ValueError as exc:
            if str(exc) == "CASE_EXISTS":
                raise HTTPException(status_code=409, detail="CASE_EXISTS") from exc
            raise
        return {"ok": True, "case": _record(case)}

    @api.post("/cases/{case_id}/evidence-references")
    def add_evidence_reference(request: Request, case_id: str, payload: AddEvidenceReference) -> dict:
        require_control_key(request)
        try:
            case = CommercialCaseStore().add_evidence_reference(
                case_id, payload.evidence_type, payload.evidence_ref
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if case is None:
            raise HTTPException(status_code=404, detail="CASE_NOT_FOUND")
        return {
            "ok": True,
            "case": _record(case),
            "evidence_reference_state": "UNVERIFIED",
            "stage_advanced": False,
            "revenue_verified": False,
            "note": "A reference is not proof; stage advancement requires independent verification.",
        }

    return api

"""Commercial operations API for Electronic Brain.

Evidence-first commercial case tracking. No external outreach, contracting,
charging, withdrawal, or funds movement is performed by this API.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from brain_v12.business.commercial_case import CommercialCase
from brain_v12.business.commercial_operations_dashboard import (
    build_commercial_operations_dashboard,
)
from brain_v12.business.initial_monetization_catalog import INITIAL_MONETIZATION_CATALOG

_CASES: dict[str, CommercialCase] = {}


class CreateCommercialCase(BaseModel):
    capability_id: str = Field(min_length=1)
    case_id: str | None = None
    prospect_evidence: str | None = None


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
        result = build_commercial_operations_dashboard(
            INITIAL_MONETIZATION_CATALOG, list(_CASES.values())
        )
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
    def cases() -> dict:
        return {"ok": True, "cases": [_record(x) for x in _CASES.values()]}

    @api.post("/cases")
    def create_case(payload: CreateCommercialCase) -> dict:
        offer = next(
            (x for x in INITIAL_MONETIZATION_CATALOG
             if x.capability_id == payload.capability_id),
            None,
        )
        if offer is None:
            raise HTTPException(status_code=404, detail="UNKNOWN_CAPABILITY")
        case_id = (payload.case_id or "").strip() or f"case-{len(_CASES)+1:04d}"
        if case_id in _CASES:
            raise HTTPException(status_code=409, detail="CASE_EXISTS")
        case = CommercialCase(
            case_id=case_id,
            capability_id=offer.capability_id,
            offer=offer.offer,
            prospect_evidence=payload.prospect_evidence,
        )
        _CASES[case_id] = case
        return {"ok": True, "case": _record(case)}

    return api

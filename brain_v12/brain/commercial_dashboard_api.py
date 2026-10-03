"""Read-only commercial operations API for Electronic Brain."""
from __future__ import annotations

from fastapi import APIRouter

from brain_v12.business.commercial_operations_dashboard import (
    build_commercial_operations_dashboard,
)
from brain_v12.business.initial_monetization_catalog import INITIAL_MONETIZATION_CATALOG


def router() -> APIRouter:
    api = APIRouter(prefix="/api/commercial", tags=["commercial"])

    @api.get("/dashboard")
    def dashboard() -> dict:
        result = build_commercial_operations_dashboard(
            INITIAL_MONETIZATION_CATALOG,
            [],
        )
        return {"ok": True, **result.to_record()}

    @api.get("/offers")
    def offers() -> dict:
        return {
            "ok": True,
            "offers": [
                {
                    "capability_id": item.capability_id,
                    "capability_name": item.capability_name,
                    "offer": item.offer,
                    "target_customer": item.target_customer,
                    "acquisition_channel": item.acquisition_channel,
                    "delivery_evidence": item.delivery_evidence,
                    "cost_model": item.cost_model,
                    "status": item.status,
                }
                for item in INITIAL_MONETIZATION_CATALOG
            ],
        }

    return api

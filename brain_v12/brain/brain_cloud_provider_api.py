"""Read-only Brain Cloud provider control-plane API.

These endpoints report configuration readiness and verified capacity. They never
provision infrastructure and never convert simulated workers into real capacity.
All endpoints require the Brain control key.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from .control_auth import require_control_key
from .brain_cloud_provider import brain_provider_inventory
from .cloud_provider_readiness import discover_provider_configuration

router = APIRouter(prefix="/api/brain-cloud/provider", tags=["Brain Cloud Provider"])


@router.get("/status")
def provider_status(request: Request) -> dict:
    require_control_key(request)
    capacity = brain_provider_inventory([])
    configuration = discover_provider_configuration()
    return {
        "ok": True,
        "provider": "brain-cloud",
        "status": capacity["status"],
        "capacity": capacity,
        "provider_configuration": configuration,
        "provisioning_supported": False,
        "note": (
            "This API is the Brain-owned control-plane surface. It does not create "
            "compute; a provider adapter and verified external worker are required."
        ),
    }


@router.get("/readiness")
def provider_readiness(request: Request) -> dict:
    require_control_key(request)
    configuration = discover_provider_configuration()
    capacity = brain_provider_inventory([])
    blockers = []
    if configuration["configured_provider_count"] == 0:
        blockers.append("NO_CONFIGURED_CLOUD_PROVIDER_CREDENTIALS")
    blockers.append("NO_VERIFIED_REAL_WORKER")
    blockers.append("PROVIDER_SPECIFIC_PROVISIONING_ADAPTER_NOT_IMPLEMENTED")
    return {
        "ok": True,
        "ready": False,
        "status": "BLOCKED",
        "blockers": blockers,
        "provider_configuration_status": configuration["status"],
        "capacity_status": capacity["status"],
        "provisioning_allowed": False,
        "secret_values_exposed": False,
    }

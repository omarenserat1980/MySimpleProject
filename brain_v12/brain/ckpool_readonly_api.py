"""Read-only FastAPI endpoint for public Solo CKPool telemetry."""
from __future__ import annotations

from fastapi import APIRouter

from .ckpool_readonly_collector import collect_ckpool_readonly

router = APIRouter(tags=["mining-readonly"])


@router.get("/api/mining/ckpool/status")
def ckpool_public_status():
    """Return public pool-wide CKPool telemetry; never starts or configures mining."""
    report = collect_ckpool_readonly()
    # Keep this endpoint observational: telemetry failures are represented in the
    # report rather than converted into a false mining-success status.
    return report

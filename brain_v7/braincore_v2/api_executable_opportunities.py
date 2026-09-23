"""Route opportunities toward permissioned API execution.

This module identifies work that can be prepared locally and optionally
completed through an explicitly connected provider API. It never bypasses
authentication, sends unsolicited submissions, or claims payment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable


@dataclass(frozen=True)
class ApiOpportunity:
    name: str
    service: str
    local_execution: bool
    api_delivery_possible: bool
    provider: str
    auth_required: bool
    payment_confirmation_required: bool = True


CATALOG = (
    ApiOpportunity("Content package", "product_copy", True, True, "connected_marketplace", True),
    ApiOpportunity("Short video delivery", "short_video", True, True, "connected_storage_or_marketplace", True),
    ApiOpportunity("Ad creative delivery", "ad_creative", True, True, "connected_storage_or_marketplace", True),
    ApiOpportunity("Listing package", "listing_package", True, True, "connected_marketplace", True),
    ApiOpportunity("Data report delivery", "data_processing", True, True, "connected_storage_or_marketplace", True),
)


def catalog() -> list[dict]:
    return [asdict(x) for x in CATALOG]


def executable_routes(
    *,
    provider_connected: bool,
    authenticated: bool,
    api_scope_authorized: bool,
) -> list[dict]:
    """Return routes that are technically eligible under current permissions."""
    if not (provider_connected and authenticated and api_scope_authorized):
        return []
    return [asdict(x) for x in CATALOG if x.api_delivery_possible]


def execution_gate(
    *,
    artifact_ready: bool,
    provider_connected: bool,
    authenticated: bool,
    api_scope_authorized: bool,
    explicit_job_authorization: bool,
) -> dict:
    blockers = []
    if not artifact_ready:
        blockers.append("ARTIFACT_NOT_READY")
    if not provider_connected:
        blockers.append("PROVIDER_NOT_CONNECTED")
    if not authenticated:
        blockers.append("PROVIDER_NOT_AUTHENTICATED")
    if not api_scope_authorized:
        blockers.append("API_SCOPE_NOT_AUTHORIZED")
    if not explicit_job_authorization:
        blockers.append("EXPLICIT_JOB_AUTHORIZATION_REQUIRED")

    return {
        "status": "READY_FOR_API_EXECUTION" if not blockers else "BLOCKED",
        "blockers": blockers,
        "payment_verified": False,
        "income_claim_allowed": False,
    }


def prioritize(items: Iterable[dict]) -> list[dict]:
    """Prefer locally executable/API-deliverable work without claiming revenue."""
    rows = list(items)
    return sorted(
        rows,
        key=lambda x: (
            bool(x.get("local_execution", False)),
            bool(x.get("api_delivery_possible", False)),
            not bool(x.get("auth_required", True)),
        ),
        reverse=True,
    )

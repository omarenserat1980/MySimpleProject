from __future__ import annotations

from typing import Any


def require_free_entitlement(preflight: dict[str, Any]) -> None:
    """Fail closed unless every cost-critical free-entitlement fact is explicit."""
    if not preflight.get("ok"):
        raise RuntimeError("REAL_CLOUD_PREFLIGHT_FAILED")
    if not preflight.get("free_capacity"):
        raise RuntimeError("FREE_CAPACITY_NOT_CONFIRMED")
    if preflight.get("estimated_cost", 0) != 0:
        raise RuntimeError("PAID_RESOURCE_BLOCKED")
    if preflight.get("free_entitlement_verified") is not True:
        raise RuntimeError("FREE_ENTITLEMENT_NOT_VERIFIED")
    if int(preflight.get("free_hours_remaining", 0)) <= 0:
        raise RuntimeError("FREE_HOURS_EXHAUSTED")
    if int(preflight.get("requested_free_hours", 0)) <= 0:
        raise RuntimeError("FREE_HOURS_REQUEST_NOT_DEFINED")
    if int(preflight.get("free_hours_remaining", 0)) < int(preflight.get("requested_free_hours", 0)):
        raise RuntimeError("FREE_HOURS_INSUFFICIENT")
    if preflight.get("dependent_resources_cost_verified_zero") is not True:
        raise RuntimeError("DEPENDENT_RESOURCE_COST_NOT_VERIFIED_ZERO")
    if preflight.get("spending_limit_protected") is not True:
        raise RuntimeError("SPENDING_PROTECTION_NOT_VERIFIED")

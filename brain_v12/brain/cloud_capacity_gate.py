"""Fail-closed gate for selecting genuinely free cloud capacity.

Decision gate only: it does not provision infrastructure or call cloud APIs.
A provider adapter must supply fresh, authenticated provider evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


@dataclass(frozen=True)
class CapacityRequest:
    """Minimum resources requested for one bounded workload."""
    vcpu: int
    memory_mb: int
    storage_gb: int = 0

    def __post_init__(self) -> None:
        if self.vcpu < 1 or self.memory_mb < 1 or self.storage_gb < 0:
            raise ValueError("CAPACITY_REQUEST_INVALID")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def evaluate_free_capacity(
    request: CapacityRequest,
    evidence: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate provider evidence without creating or changing resources.

    A provider adapter must set provider_verified only after authenticating a
    provider response. Manually authored JSON is not proof.
    """
    instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    observed = _parse_time(evidence.get("observed_at"))
    expires = _parse_time(evidence.get("expires_at"))
    try:
        cost = Decimal(str(evidence.get("estimated_monthly_cost_usd")))
    except (InvalidOperation, TypeError, ValueError):
        cost = Decimal("-1")

    checks = {
        "provider_verified": evidence.get("provider_verified") is True,
        "provider_identified": bool(str(evidence.get("provider", "")).strip()),
        "region_identified": bool(str(evidence.get("region", "")).strip()),
        "sku_identified": bool(str(evidence.get("sku", "")).strip()),
        "evidence_source_present": bool(str(evidence.get("source_ref", "")).strip()),
        "evidence_timestamp_valid": observed is not None and observed <= instant,
        "evidence_not_expired": expires is not None and instant < expires,
        "free_tier_confirmed": evidence.get("free_tier_eligible") is True,
        "zero_cost_confirmed": cost == Decimal("0"),
        "vcpu_sufficient": _is_int(evidence.get("available_vcpu")) and evidence["available_vcpu"] >= request.vcpu,
        "memory_sufficient": _is_int(evidence.get("available_memory_mb")) and evidence["available_memory_mb"] >= request.memory_mb,
        "storage_sufficient": _is_int(evidence.get("available_storage_gb")) and evidence["available_storage_gb"] >= request.storage_gb,
    }
    eligible = all(checks.values())
    return {
        "schema": "brain.free-cloud-capacity-gate.v1",
        "status": "ELIGIBLE" if eligible else "BLOCKED",
        "eligible": eligible,
        "provisioning_performed": False,
        "paid_fallback_allowed": False,
        "provider": str(evidence.get("provider", "")) if evidence.get("provider") else None,
        "region": str(evidence.get("region", "")) if evidence.get("region") else None,
        "sku": str(evidence.get("sku", "")) if evidence.get("sku") else None,
        "requested": {"vcpu": request.vcpu, "memory_mb": request.memory_mb, "storage_gb": request.storage_gb},
        "checks": checks,
        "blocked_reasons": [name for name, passed in checks.items() if not passed],
        "evidence_source_ref": evidence.get("source_ref"),
        "evaluated_at": instant.isoformat(),
        "rule": "Require fresh provider-verified capacity evidence and confirmed zero cost; never provision.",
    }

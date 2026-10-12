"""Canonical, evidence-backed status indicators for Brain software nodes.

Indicators are deliberately conservative: missing, stale, or insufficient
evidence never becomes a green/healthy status. This module is pure and does
not contact external devices or execution backends.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VerificationLevel(str, Enum):
    CONFIGURED = "CONFIGURED"
    REGISTERED = "REGISTERED"
    BACKEND_VERIFIED = "BACKEND_VERIFIED"
    RESOURCE_OBSERVED = "RESOURCE_OBSERVED"
    EXECUTION_VERIFIED = "EXECUTION_VERIFIED"
    GUEST_BOOT_VERIFIED = "GUEST_BOOT_VERIFIED"
    RUNTIME_HEALTH_VERIFIED = "RUNTIME_HEALTH_VERIFIED"


_LEVEL_RANK = {level: index for index, level in enumerate(VerificationLevel)}


@dataclass(frozen=True)
class CanonicalIndicator:
    indicator_id: str
    subject_id: str
    indicator_type: str
    value: Any
    status: str
    source: str
    backend_id: str | None
    observed_at: str | None
    verified_at: str | None
    verification_level: str
    evidence_refs: tuple[str, ...] = ()
    error_code: str | None = None
    schema_version: str = "brain.indicator.v1"

    def public(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence_refs"] = list(self.evidence_refs)
        return result


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str | datetime | None) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_indicator(
    *,
    indicator_id: str,
    subject_id: str,
    indicator_type: str,
    value: Any,
    source: str,
    verification_level: VerificationLevel | str,
    observed_at: str | datetime | None,
    evidence_refs: tuple[str, ...] | list[str] = (),
    backend_id: str | None = None,
    verified_at: str | datetime | None = None,
    freshness_seconds: int = 300,
    required_level: VerificationLevel | str = VerificationLevel.CONFIGURED,
    error_code: str | None = None,
    now: datetime | None = None,
) -> CanonicalIndicator:
    """Create a truthful indicator with deterministic freshness/evidence gates.

    The value is preserved for diagnostics, but the resulting status is not
    verified unless identity, evidence level, timestamp, and freshness pass.
    """
    if not indicator_id.strip() or not subject_id.strip() or not source.strip():
        raise ValueError("INDICATOR_ID_SUBJECT_AND_SOURCE_REQUIRED")
    if freshness_seconds < 0:
        raise ValueError("INDICATOR_FRESHNESS_MUST_BE_NONNEGATIVE")

    level = VerificationLevel(verification_level)
    required = VerificationLevel(required_level)
    observed = _parse_timestamp(observed_at)
    verified = _parse_timestamp(verified_at)
    current = (now or utc_now()).astimezone(timezone.utc)
    evidence = tuple(str(item) for item in evidence_refs if str(item).strip())

    status = "UNKNOWN"
    code = error_code
    if observed is None:
        status, code = "UNKNOWN", code or "INDICATOR_OBSERVATION_MISSING_OR_INVALID"
    elif (current - observed).total_seconds() > freshness_seconds:
        status, code = "STALE", code or "INDICATOR_EVIDENCE_STALE"
    elif (observed - current).total_seconds() > 30:
        status, code = "UNKNOWN", code or "INDICATOR_OBSERVATION_IN_FUTURE"
    elif _LEVEL_RANK[level] < _LEVEL_RANK[required]:
        status, code = "UNVERIFIED", code or "INDICATOR_VERIFICATION_LEVEL_INSUFFICIENT"
    elif _LEVEL_RANK[level] >= _LEVEL_RANK[VerificationLevel.EXECUTION_VERIFIED] and not evidence:
        status, code = "UNVERIFIED", code or "INDICATOR_EVIDENCE_REFERENCE_REQUIRED"
    elif verified is not None and verified > current:
        status, code = "UNKNOWN", code or "INDICATOR_VERIFICATION_TIMESTAMP_IN_FUTURE"
    else:
        status = "VERIFIED"
        code = None

    return CanonicalIndicator(
        indicator_id=indicator_id,
        subject_id=subject_id,
        indicator_type=indicator_type,
        value=value,
        status=status,
        source=source,
        backend_id=backend_id,
        observed_at=observed.isoformat().replace("+00:00", "Z") if observed else None,
        verified_at=verified.isoformat().replace("+00:00", "Z") if verified else None,
        verification_level=level.value,
        evidence_refs=evidence,
        error_code=code,
    )


def aggregate_required_indicators(
    indicators: list[CanonicalIndicator],
) -> dict[str, Any]:
    """Aggregate required component indicators without hiding uncertainty."""
    if not indicators:
        return {
            "status": "UNKNOWN",
            "healthy": False,
            "required_count": 0,
            "verified_count": 0,
            "blockers": ["NO_REQUIRED_INDICATORS"],
        }
    blockers = [
        {
            "indicator_id": item.indicator_id,
            "subject_id": item.subject_id,
            "status": item.status,
            "error_code": item.error_code,
        }
        for item in indicators
        if item.status != "VERIFIED"
    ]
    healthy = not blockers
    return {
        "status": "HEALTHY" if healthy else "DEGRADED",
        "healthy": healthy,
        "required_count": len(indicators),
        "verified_count": len(indicators) - len(blockers),
        "blockers": blockers,
    }

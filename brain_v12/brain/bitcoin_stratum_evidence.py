"""Fail-closed schema checks for externally collected Bitcoin Stratum evidence.

This module does not connect to a pool, run a miner, or authenticate the source.
A valid digest proves integrity only when the expected digest is obtained through
a trusted channel; it does not prove that the payload describes a real worker.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any


REQUIRED = {
    "schema_version", "worker_id", "algorithm", "pool_host", "observed_at",
    "window_seconds", "hashrate_hs", "accepted_shares", "rejected_shares",
    "stale_shares", "connection_state", "evidence_sha256",
}


def canonical_sha256(payload: dict[str, Any]) -> str:
    """Hash canonical evidence excluding its self-referential digest field."""
    clean = {k: v for k, v in payload.items() if k != "evidence_sha256"}
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_stratum_evidence(
    payload: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Validate evidence shape, freshness, and internal digest; never authorize mining."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {"valid": False, "status": "BLOCKED_INVALID_EVIDENCE", "errors": ["PAYLOAD_NOT_OBJECT"],
                "execution_authorized": False, "revenue_verified": False}
    missing = sorted(REQUIRED - payload.keys())
    if missing:
        errors.append("MISSING_FIELDS:" + ",".join(missing))
    if missing:
        return {"valid": False, "status": "BLOCKED_INVALID_EVIDENCE", "errors": errors,
                "execution_authorized": False, "revenue_verified": False}

    if payload.get("schema_version") != 1:
        errors.append("UNSUPPORTED_SCHEMA_VERSION")
    for key in ("worker_id", "pool_host"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            errors.append("INVALID_" + key.upper())
    if str(payload.get("algorithm", "")).lower() not in {"sha256d", "sha-256d"}:
        errors.append("ALGORITHM_NOT_BITCOIN_SHA256D")
    if payload.get("connection_state") != "CONNECTED":
        errors.append("POOL_NOT_CONNECTED")
    for key in ("window_seconds", "accepted_shares", "rejected_shares", "stale_shares"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            errors.append("INVALID_" + key.upper())
    rate = payload.get("hashrate_hs")
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate < 0:
        errors.append("INVALID_HASHRATE_HS")
    try:
        observed = datetime.fromisoformat(str(payload.get("observed_at", "")).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("timezone required")
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        age = (current - observed.astimezone(timezone.utc)).total_seconds()
        if age < -30:
            errors.append("OBSERVATION_FROM_FUTURE")
        elif age > max_age_seconds:
            errors.append("STALE_EVIDENCE")
    except (TypeError, ValueError, OverflowError):
        errors.append("INVALID_OBSERVED_AT")
        age = None
    expected = canonical_sha256(payload)
    if not isinstance(payload.get("evidence_sha256"), str) or payload["evidence_sha256"] != expected:
        errors.append("EVIDENCE_DIGEST_MISMATCH")

    return {
        "valid": not errors,
        "status": "SCHEMA_AND_INTEGRITY_VALID" if not errors else "BLOCKED_INVALID_EVIDENCE",
        "errors": errors,
        "observed_age_seconds": round(age, 3) if age is not None else None,
        "evidence_sha256": expected,
        "execution_authorized": False,
        "revenue_verified": False,
        "limitations": [
            "Internal digest is not source authentication.",
            "No pool connection was made by this validator.",
            "Accepted-share values are untrusted until independently sourced.",
            "Payout and wallet receipt require separate independent verification.",
        ],
    }

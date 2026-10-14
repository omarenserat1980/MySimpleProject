"""Fail-closed validator for Bitcoin pool evidence artifacts.

This module validates supplied records; it does not connect to a pool, authenticate
a worker, or independently verify that a claimed pool API response is genuine.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from typing import Any


def _utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def evidence_digest(record: dict[str, Any]) -> str:
    """Hash canonical JSON excluding the digest field itself."""
    payload = {key: value for key, value in record.items() if key != "evidence_artifact_sha256"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_pool_evidence(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Validate a live Bitcoin pool evidence record; never claims payout or revenue."""
    errors: list[str] = []
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not isinstance(record, dict):
        return {"status": "BLOCKED", "errors": ["RECORD_NOT_OBJECT"], "mining_activity_verified": False, "payout_verified": False, "revenue_verified": False}
    if record.get("schema_version") != "1.0":
        errors.append("UNSUPPORTED_SCHEMA_VERSION")
    if record.get("mode") != "live":
        errors.append("LIVE_MODE_REQUIRED")
    if record.get("fixture") is not False:
        errors.append("FIXTURE_OR_UNMARKED_EVIDENCE_FORBIDDEN")

    observed = _utc_timestamp(record.get("observed_at_utc"))
    if observed is None:
        errors.append("INVALID_OBSERVATION_TIMESTAMP")
    else:
        age = (now.astimezone(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
        if age < -30:
            errors.append("OBSERVATION_TIMESTAMP_IN_FUTURE")
        elif age > max_age_seconds:
            errors.append("STALE_EVIDENCE")

    worker_id = record.get("worker_id")
    if not isinstance(worker_id, str) or not worker_id.strip():
        errors.append("WORKER_ID_REQUIRED")

    pool = record.get("pool")
    if not isinstance(pool, dict):
        errors.append("POOL_OBJECT_REQUIRED")
        pool = {}
    if not isinstance(pool.get("host"), str) or not pool["host"].strip():
        errors.append("POOL_HOST_REQUIRED")
    if not isinstance(pool.get("port"), int) or isinstance(pool.get("port"), bool) or not 1 <= pool["port"] <= 65535:
        errors.append("INVALID_POOL_PORT")
    if pool.get("protocol") != "stratum":
        errors.append("STRATUM_PROTOCOL_REQUIRED")
    if pool.get("connected") is not True or pool.get("authorized") is not True:
        errors.append("POOL_CONNECTION_AND_AUTHORIZATION_REQUIRED")
    if _utc_timestamp(pool.get("connected_at_utc")) is None:
        errors.append("INVALID_POOL_CONNECTION_TIMESTAMP")
    if pool.get("source") not in {"pool-api", "worker"}:
        errors.append("POOL_SOURCE_REQUIRED")

    hashrate = record.get("hashrate")
    if not isinstance(hashrate, dict):
        errors.append("HASHRATE_OBJECT_REQUIRED")
        hashrate = {}
    value = hashrate.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        errors.append("POSITIVE_MEASURED_HASHRATE_REQUIRED")
    if hashrate.get("unit") != "H/s":
        errors.append("HASHRATE_UNIT_MUST_BE_HS")
    window = hashrate.get("window_seconds")
    if not isinstance(window, int) or isinstance(window, bool) or window <= 0:
        errors.append("HASHRATE_WINDOW_REQUIRED")
    if hashrate.get("source") not in {"pool-api", "worker"}:
        errors.append("HASHRATE_SOURCE_REQUIRED")

    shares = record.get("shares")
    if not isinstance(shares, dict):
        errors.append("SHARES_OBJECT_REQUIRED")
        shares = {}
    for field in ("accepted_total", "accepted_interval", "rejected_total", "stale_total"):
        number = shares.get(field)
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            errors.append("INVALID_SHARE_COUNTER_" + field.upper())
    if isinstance(shares.get("accepted_interval"), int) and not isinstance(shares.get("accepted_interval"), bool) and shares["accepted_interval"] < 1:
        errors.append("AT_LEAST_ONE_ACCEPTED_SHARE_REQUIRED")
    if shares.get("source") != "pool-api":
        errors.append("POOL_SIDE_SHARE_EVIDENCE_REQUIRED")

    digest = record.get("evidence_artifact_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        errors.append("INVALID_EVIDENCE_DIGEST")
    elif digest != evidence_digest(record):
        errors.append("EVIDENCE_DIGEST_MISMATCH")

    passed = not errors
    return {
        "status": "MINING_ACTIVITY_EVIDENCE_VALIDATED" if passed else "BLOCKED",
        "errors": errors,
        "mining_activity_verified": passed,
        "payout_verified": False,
        "revenue_verified": False,
        "evidence_limit": "Schema, freshness and digest checks do not authenticate the source. Pool payout and wallet-side receipt require separate independent evidence.",
    }

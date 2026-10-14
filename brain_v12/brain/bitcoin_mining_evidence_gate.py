"""Fail-closed validation for Bitcoin live-mining evidence.

This module validates evidence only; it never connects to a pool or starts a miner.
The artifact digest is SHA-256 over canonical JSON after removing
'evidence_artifact_sha256'. Fixture and dry-run evidence can never pass.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def canonical_digest(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("evidence_artifact_sha256", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_live_mining_evidence(
    record: dict[str, Any],
    *,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Return a machine-readable gate report. Missing/invalid evidence fails closed."""
    failures: list[str] = []
    if not isinstance(record, dict):
        return {"status": "BLOCKED", "gate": "MINING_ACTIVITY_VERIFIED", "failures": ["record_not_object"]}

    if record.get("schema_version") != "1.0":
        failures.append("unsupported_schema_version")
    if record.get("mode") != "live":
        failures.append("not_live_mode")
    if record.get("fixture") is not False:
        failures.append("fixture_or_fixture_flag_missing")
    worker_id = record.get("worker_id")
    if not isinstance(worker_id, str) or not worker_id.strip():
        failures.append("worker_identity_missing")

    observed = _parse_utc(record.get("observed_at_utc"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    if observed is None:
        failures.append("invalid_observation_timestamp")
    else:
        age = (current - observed).total_seconds()
        if age < -30:
            failures.append("observation_timestamp_in_future")
        elif age > max_age_seconds:
            failures.append("evidence_stale")

    pool = record.get("pool")
    if not isinstance(pool, dict):
        failures.append("pool_evidence_missing")
        pool = {}
    if pool.get("protocol") != "stratum":
        failures.append("unsupported_or_missing_protocol")
    if pool.get("connected") is not True:
        failures.append("pool_connection_not_confirmed")
    if pool.get("authorized") is not True:
        failures.append("pool_authorization_not_confirmed")
    if not isinstance(pool.get("host"), str) or not pool.get("host", "").strip():
        failures.append("pool_host_missing")
    if not isinstance(pool.get("port"), int) or isinstance(pool.get("port"), bool) or not 1 <= pool.get("port", 0) <= 65535:
        failures.append("pool_port_invalid")
    if not isinstance(pool.get("source"), str) or not pool.get("source", "").strip():
        failures.append("pool_source_missing")
    if _parse_utc(pool.get("connected_at_utc")) is None:
        failures.append("invalid_pool_connection_timestamp")

    hashrate = record.get("hashrate")
    if not isinstance(hashrate, dict):
        failures.append("hashrate_evidence_missing")
        hashrate = {}
    value = hashrate.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        failures.append("hashrate_not_positive_finite_measurement")
    if not isinstance(hashrate.get("unit"), str) or not hashrate.get("unit", "").strip():
        failures.append("hashrate_unit_missing")
    window = hashrate.get("window_seconds")
    if isinstance(window, bool) or not isinstance(window, int) or window <= 0:
        failures.append("hashrate_window_invalid")
    if not isinstance(hashrate.get("source"), str) or not hashrate.get("source", "").strip():
        failures.append("hashrate_source_missing")

    shares = record.get("shares")
    if not isinstance(shares, dict):
        failures.append("share_evidence_missing")
        shares = {}
    for field in ("accepted_total", "accepted_interval", "rejected_total", "stale_total"):
        count = shares.get(field)
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            failures.append(f"share_counter_invalid:{field}")
    if isinstance(shares.get("accepted_total"), int) and not isinstance(shares.get("accepted_total"), bool) and shares["accepted_total"] < 1:
        failures.append("no_accepted_share")
    if isinstance(shares.get("accepted_interval"), int) and not isinstance(shares.get("accepted_interval"), bool) and shares["accepted_interval"] < 1:
        failures.append("no_accepted_share_in_interval")
    if not isinstance(shares.get("source"), str) or not shares.get("source", "").strip():
        failures.append("share_source_missing")

    supplied_digest = record.get("evidence_artifact_sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64 or any(c not in "0123456789abcdef" for c in supplied_digest):
        failures.append("evidence_digest_missing_or_invalid")
    elif supplied_digest != canonical_digest(record):
        failures.append("evidence_digest_mismatch")

    return {
        "status": "PASS" if not failures else "BLOCKED",
        "gate": "MINING_ACTIVITY_VERIFIED",
        "worker_id": worker_id if isinstance(worker_id, str) else None,
        "observed_at_utc": record.get("observed_at_utc"),
        "failures": failures,
        "revenue_status": "NOT_ASSESSED_BY_MINING_ACTIVITY_GATE",
        "note": "A passing activity gate does not prove payout, BTC receipt, or profitability.",
    }

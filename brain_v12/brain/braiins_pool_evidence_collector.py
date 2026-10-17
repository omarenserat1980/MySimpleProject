"""Read-only, independently sourced Braiins Pool worker telemetry.

This collector performs exactly one HTTPS GET to Braiins Pool's documented
workers endpoint. It never submits shares, starts a miner, changes pool settings,
reads wallet/payout endpoints, or treats pool telemetry as proof Brain computed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from typing import Any, Callable

import httpx

BRAIINS_WORKERS_URL = "https://pool.braiins.com/accounts/workers/json/btc"
MAX_RESPONSE_BYTES = 1_000_000
WORKER_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "BLOCKED",
        "reason": reason,
        "pool_activity_verified": False,
        "accepted_share_submission_verified": False,
        "brain_runtime_activity_verified": False,
        "payout_verified": False,
        "revenue_verified": False,
        "network_access_performed": False,
        "pool_settings_changed": False,
        "miner_started": False,
        "pool_credential_scope_verified": False,
        "operator_must_use_read_only_access_profile": True,
    }


def collect_braiins_pool_evidence(
    *,
    api_token: str | None = None,
    expected_worker_id: str | None = None,
    client_factory: Callable[..., Any] | None = None,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Fetch and verify one read-only pool telemetry snapshot.

    In production the default HTTPX client validates TLS certificates. Tests may
    inject a fake client; their results are fixtures, never real-world evidence.
    The token is used only as a request header and is never returned or logged.
    """
    token = api_token if api_token is not None else os.environ.get("BRAIINS_POOL_API_TOKEN", "")
    worker_id = expected_worker_id if expected_worker_id is not None else os.environ.get("BRAIINS_POOL_WORKER_ID", "")
    if not isinstance(token, str) or not token.strip():
        return _blocked("READ_ONLY_POOL_API_TOKEN_NOT_CONFIGURED")
    if not isinstance(worker_id, str) or not WORKER_ID_PATTERN.fullmatch(worker_id):
        return _blocked("EXPECTED_POOL_WORKER_ID_NOT_CONFIGURED_OR_INVALID")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or not 1 <= max_age_seconds <= 3600:
        return _blocked("INVALID_MAX_AGE_SECONDS")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        return _blocked("TIMEZONE_AWARE_CLOCK_REQUIRED")

    factory = client_factory or httpx.Client
    try:
        # Fixed HTTPS URL, GET only, verified TLS, no redirects, bounded timeout.
        with factory(verify=True, timeout=10.0, follow_redirects=False) as client:
            response = client.get(BRAIINS_WORKERS_URL, headers={"Pool-Auth-Token": token})
    except Exception as exc:  # Do not leak exception strings, request headers, or credentials.
        result = _blocked("POOL_API_REQUEST_FAILED")
        result["error_type"] = type(exc).__name__
        result["network_access_performed"] = True
        return result

    try:
        response_url = str(response.url)
        response_history = getattr(response, "history", ())
        status_code = response.status_code
        content = response.content
    except Exception:
        result = _blocked("POOL_API_RESPONSE_INVALID")
        result["network_access_performed"] = True
        return result
    if response_url.rstrip("/") != BRAIINS_WORKERS_URL.rstrip("/") or response_history:
        result = _blocked("UNEXPECTED_POOL_API_URL_OR_REDIRECT")
        result["network_access_performed"] = True
        return result
    if status_code != 200:
        result = _blocked("POOL_API_HTTP_STATUS_NOT_200")
        result.update({"http_status": status_code, "network_access_performed": True})
        return result
    if not isinstance(content, bytes) or len(content) > MAX_RESPONSE_BYTES:
        result = _blocked("POOL_API_RESPONSE_SIZE_INVALID")
        result["network_access_performed"] = True
        return result
    try:
        payload = response.json()
        workers = payload["btc"]["workers"]
        if not isinstance(workers, dict):
            raise ValueError("workers must be an object")
    except Exception:
        result = _blocked("POOL_API_WORKERS_PAYLOAD_INVALID")
        result["network_access_performed"] = True
        return result

    worker = workers.get(worker_id)
    if not isinstance(worker, dict):
        result = _blocked("EXPECTED_WORKER_NOT_FOUND_IN_POOL_RESPONSE")
        result.update({
            "http_status": 200,
            "pool_endpoint": BRAIINS_WORKERS_URL,
            "pool_response_sha256": hashlib.sha256(content).hexdigest(),
            "pool_source_authenticated_over_https": True,
            "network_access_performed": True,
        })
        return result

    try:
        state = worker.get("state")
        hashrate = worker.get("hash_rate_5m")
        shares = worker.get("shares_5m")
        last_share = worker.get("last_share")
        if isinstance(hashrate, bool) or not isinstance(hashrate, (int, float, str)):
            raise ValueError("invalid hashrate")
        hashrate = float(hashrate)
        if not math.isfinite(hashrate) or hashrate < 0:
            raise ValueError("invalid hashrate")
        if isinstance(shares, bool) or not isinstance(shares, (int, float, str)):
            raise ValueError("invalid share counter")
        shares_float = float(shares)
        if not math.isfinite(shares_float) or shares_float < 0 or not shares_float.is_integer():
            raise ValueError("invalid share counter")
        shares = int(shares_float)
        if isinstance(last_share, bool) or not isinstance(last_share, (int, float, str)):
            raise ValueError("invalid last_share")
        last_share_float = float(last_share)
        if not math.isfinite(last_share_float) or last_share_float <= 0 or not last_share_float.is_integer():
            raise ValueError("invalid last_share")
        last_share = int(last_share_float)
        unit = worker.get("hash_rate_unit")
        if not isinstance(unit, str) or unit.strip().casefold() not in {"h/s", "kh/s", "mh/s", "gh/s", "th/s", "ph/s", "eh/s"}:
            raise ValueError("invalid hashrate unit")
    except (TypeError, ValueError, OverflowError):
        result = _blocked("POOL_WORKER_METRICS_INVALID")
        result.update({"http_status": 200, "pool_source_authenticated_over_https": True,
                       "network_access_performed": True})
        return result

    age = current.timestamp() - last_share
    response_digest = hashlib.sha256(content).hexdigest()
    common = {
        "http_status": 200,
        "pool_endpoint": BRAIINS_WORKERS_URL,
        "pool_response_sha256": response_digest,
        "pool_source_authenticated_over_https": True,
        "pool_credential_scope_verified": False,
        "operator_must_use_read_only_access_profile": True,
        "worker_id": worker_id,
        "worker_state": state,
        "hashrate_5m_provider_units": hashrate,
        "hashrate_unit": worker.get("hash_rate_unit"),
        "shares_5m_pool_reported": shares,
        "last_share_age_seconds": round(age, 3),
        "observed_at_utc": current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "network_access_performed": True,
        "pool_settings_changed": False,
        "miner_started": False,
        "accepted_share_submission_verified": False,
        "brain_runtime_activity_verified": False,
        "payout_verified": False,
        "revenue_verified": False,
        "evidence_limit": "This is independent pool-side aggregate telemetry, not per-share submission proof and not proof that Brain produced the work.",
    }
    if state not in {"ok", "low"} or hashrate <= 0 or shares < 1:
        return {"ok": False, "status": "POOL_ACTIVITY_NOT_ESTABLISHED", "pool_activity_verified": False,
                "reason": "POSITIVE_POOL_HASHRATE_AND_RECENT_POOL_REPORTED_SHARES_REQUIRED", **common}
    if age < -30 or age > max_age_seconds:
        return {"ok": False, "status": "BLOCKED_STALE_POOL_ACTIVITY", "pool_activity_verified": False,
                "reason": "POOL_LAST_SHARE_OUTSIDE_FRESHNESS_WINDOW", **common}
    return {
        "ok": True,
        "status": "POOL_ACTIVITY_OBSERVED",
        "pool_activity_verified": True,
        "proof_level": "INDEPENDENT_POOL_API_AGGREGATE_TELEMETRY",
        "reason": None,
        **common,
    }

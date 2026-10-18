"""Challenge/HMAC ingestion for the physical ASIC telemetry bridge.

Device IDs must be explicitly enrolled with BRAIN_ASIC_DEVICE_IDS.
The in-memory nonce cache is suitable for a single API process only; use a
shared durable nonce store before running multiple replicas.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()
_lock = threading.Lock()
_challenges: dict[str, dict[str, Any]] = {}
_seen_reports: set[str] = set()
CHALLENGE_TTL_SECONDS = 90
MAX_REPORT_AGE_SECONDS = 180


def _key() -> str:
    return os.getenv("BRAIN_ASIC_HMAC_KEY", "")


def _enrolled(device_id: str) -> bool:
    raw = os.getenv("BRAIN_ASIC_DEVICE_IDS", "")
    return bool(device_id and device_id in {x.strip() for x in raw.split(",") if x.strip()})


def _canonical(report: dict[str, Any]) -> bytes:
    return json.dumps(report, sort_keys=True, separators=(",", ":")).encode()


def verify_report(report: dict[str, Any], supplied_signature: str, *, now: float | None = None) -> dict[str, Any]:
    key = _key()
    if len(key.encode()) < 32:
        raise ValueError("ASIC_INGEST_KEY_NOT_CONFIGURED")
    if not isinstance(report, dict):
        raise ValueError("ASIC_REPORT_INVALID")
    device_id = str(report.get("device_id", "")).strip()
    if not _enrolled(device_id):
        raise ValueError("ASIC_DEVICE_NOT_ENROLLED")
    if report.get("schema") != "brain-physical-asic-attestation/v1":
        raise ValueError("ASIC_SCHEMA_INVALID")
    if report.get("execution_mode") != "PHYSICAL_DEVICE":
        raise ValueError("ASIC_EXECUTION_MODE_INVALID")
    expected = hmac.new(key.encode(), _canonical(report), hashlib.sha256).hexdigest()
    if not supplied_signature or not hmac.compare_digest(expected, supplied_signature):
        raise ValueError("ASIC_HMAC_INVALID")
    try:
        observed = datetime.fromisoformat(str(report.get("observed_at", "")).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("ASIC_TIMESTAMP_MISSING_TIMEZONE")
        age = (datetime.fromtimestamp(now or time.time(), timezone.utc) - observed.astimezone(timezone.utc)).total_seconds()
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("ASIC_TIMESTAMP_INVALID") from exc
    if age < -30 or age > MAX_REPORT_AGE_SECONDS:
        raise ValueError("ASIC_REPORT_STALE")
    challenge_id = str(report.get("challenge_id", ""))
    nonce = str(report.get("challenge_nonce", ""))
    if not challenge_id or not nonce:
        raise ValueError("ASIC_CHALLENGE_REQUIRED")
    with _lock:
        challenge = _challenges.pop(challenge_id, None)
        if not challenge:
            raise ValueError("ASIC_CHALLENGE_UNKNOWN_OR_REPLAYED")
        if challenge["device_id"] != device_id or not hmac.compare_digest(challenge["nonce"], nonce):
            raise ValueError("ASIC_CHALLENGE_MISMATCH")
        if time.time() - challenge["created_at"] > CHALLENGE_TTL_SECONDS:
            raise ValueError("ASIC_CHALLENGE_EXPIRED")
        digest = hashlib.sha256(_canonical(report)).hexdigest()
        if digest in _seen_reports:
            raise ValueError("ASIC_REPORT_REPLAYED")
        _seen_reports.add(digest)
    evidence = report.get("physical_evidence", {})
    live = (
        isinstance(evidence, dict)
        and evidence.get("device_api_responded") is True
        and evidence.get("live_work_counters_present") is True
        and report.get("hashrate_mhs", 0) > 0
        and report.get("elapsed_seconds", 0) > 0
    )
    return {
        "device_id": device_id,
        "status": "PHYSICAL_DEVICE_API_CONNECTED" if live else "PHYSICAL_DEVICE_SEEN_UNVERIFIED",
        "device_api_challenge_verified": True,
        "live_telemetry_present": bool(live),
        "physical_silicon_provenance_verified": False,
        "pool_acceptance_verified": False,
        "revenue_verified": False,
        "raw_response_sha256": report.get("raw_response_sha256"),
        "received_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/asic/physical/telemetry/challenge")
async def issue_challenge(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="ASIC_JSON_REQUIRED") from exc
    device_id = str(payload.get("device_id", "")).strip() if isinstance(payload, dict) else ""
    if len(_key().encode()) < 32:
        raise HTTPException(status_code=503, detail="ASIC_INGEST_KEY_NOT_CONFIGURED")
    if not _enrolled(device_id):
        raise HTTPException(status_code=403, detail="ASIC_DEVICE_NOT_ENROLLED")
    challenge_id = secrets.token_urlsafe(18)
    nonce = secrets.token_urlsafe(32)
    now = time.time()
    with _lock:
        expired = [key for key, value in _challenges.items() if now - value["created_at"] > CHALLENGE_TTL_SECONDS]
        for key in expired:
            _challenges.pop(key, None)
        _challenges[challenge_id] = {"device_id": device_id, "nonce": nonce, "created_at": now}
    return {"ok": True, "challenge_id": challenge_id, "nonce": nonce, "expires_in_seconds": CHALLENGE_TTL_SECONDS}


@router.post("/api/asic/physical/telemetry")
async def ingest_telemetry(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="ASIC_JSON_REQUIRED") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("report"), dict):
        raise HTTPException(status_code=400, detail="ASIC_REPORT_REQUIRED")
    try:
        result = verify_report(payload["report"], str(payload.get("hmac_sha256", "")))
    except ValueError as exc:
        code = str(exc)
        status = 503 if code == "ASIC_INGEST_KEY_NOT_CONFIGURED" else 403 if "ENROLLED" in code or "HMAC" in code else 422
        raise HTTPException(status_code=status, detail=code) from exc
    return {"ok": True, "evidence": result}

"""Authenticated telemetry intake for an owner-authorized physical Bitcoin worker.

This endpoint records worker-reported telemetry only. It does not start mining,
execute remote commands, handle wallet funds, or independently verify pool shares.
Configure BRAIN_MINING_WORKER_API_TOKEN outside source control and serve behind HTTPS.
"""
from __future__ import annotations

import hmac
import math
import os
import re
import time
from threading import Lock
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field, validator

router = APIRouter(prefix="/api/bitcoin-mining/worker", tags=["Physical Bitcoin Worker"])
_lock = Lock()
_latest: dict[str, dict] = {}
REPORT_TTL_SECONDS = 120


class WorkerHeartbeat(BaseModel):
    worker_id: str = Field(min_length=1, max_length=128)
    algorithm: Literal["sha256d"]
    hashrate_hs: float = Field(ge=0, le=1e30)
    accepted_shares: int = Field(ge=0, le=10**15)
    rejected_shares: int = Field(ge=0, le=10**15)
    stale_shares: int = Field(default=0, ge=0, le=10**15)
    observed_at: float = Field(gt=0)

    @validator("worker_id")
    @classmethod
    def require_safe_worker_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value):
            raise ValueError("WORKER_ID_FORMAT_INVALID")
        return value

    @validator("hashrate_hs", "observed_at")
    @classmethod
    def require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("FINITE_NUMBER_REQUIRED")
        return value


def _authorize(authorization: str | None) -> None:
    expected = os.environ.get("BRAIN_MINING_WORKER_API_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="WORKER_API_TOKEN_NOT_CONFIGURED")
    supplied = authorization or ""
    if not supplied.startswith("Bearer ") or not hmac.compare_digest(
        supplied[7:].encode(), expected.encode()
    ):
        raise HTTPException(status_code=401, detail="WORKER_AUTHENTICATION_FAILED")


@router.post("/heartbeat")
def worker_heartbeat(
    report: WorkerHeartbeat,
    authorization: str | None = Header(default=None),
) -> dict:
    _authorize(authorization)
    now = time.time()
    if report.observed_at > now + 15:
        raise HTTPException(status_code=422, detail="OBSERVATION_TIME_IN_FUTURE")
    if now - report.observed_at > REPORT_TTL_SECONDS:
        raise HTTPException(status_code=422, detail="WORKER_REPORT_STALE")
    record = report.model_dump()
    record.update({
        "received_at": now,
        "online": True,
        "source": "authenticated_worker_self_report",
        "pool_shares_independently_verified": False,
        "payout_verified": False,
    })
    with _lock:
        _latest[report.worker_id] = record
    return {
        "ok": True,
        "worker_id": report.worker_id,
        "accepted": True,
        "source": "authenticated_worker_self_report",
        "pool_shares_independently_verified": False,
        "payout_verified": False,
    }


@router.get("/status")
def worker_status(authorization: str | None = Header(default=None)) -> dict:
    _authorize(authorization)
    now = time.time()
    # Expire stale in-memory records instead of retaining dead workers forever.
    # This endpoint is a live-status view, not a durable evidence archive.
    with _lock:
        expired_ids = [
            worker_id for worker_id, item in _latest.items()
            if now - item["received_at"] > REPORT_TTL_SECONDS
        ]
        for worker_id in expired_ids:
            del _latest[worker_id]
        workers = [dict(item, online=True) for item in _latest.values()]
    return {
        "ok": True,
        "mode": "physical_worker_telemetry_intake",
        "workers": workers,
        "worker_count": len(workers),
        "accepted_pool_shares_verified": False,
        "payout_verified": False,
        "note": "Worker reports are not independent pool-side proof.",
    }

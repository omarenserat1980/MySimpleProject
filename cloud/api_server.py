"""Minimal authenticated control/health API for the Brain runtime.

No arbitrary shell, credential, or filesystem control is exposed here.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

STATE = Path(os.getenv("BRAIN_STATE_DIR", "/app/.brain_state"))
STARTED = time.time()
TOKEN = os.getenv("BRAIN_CONTROL_TOKEN", "")
app = FastAPI(title="Electronic Brain Control Plane", docs_url=None, redoc_url=None)


def require_auth(authorization: str | None = Header(default=None)) -> None:
    if not TOKEN:
        raise HTTPException(status_code=503, detail="control plane token is not configured")
    expected = "Bearer " + TOKEN
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_seconds": round(time.time() - STARTED, 1)}


@app.get("/readyz")
def readyz():
    STATE.mkdir(parents=True, exist_ok=True)
    return {"ready": STATE.is_dir() and os.access(STATE, os.W_OK)}


@app.get("/v1/status", dependencies=[Depends(require_auth)])
def status():
    return JSONResponse({
        "service": "electronic-brain",
        "mode": os.getenv("BRAIN_CLOUD_MODE", "internet-connected"),
        "goals": [g.strip() for g in os.getenv("BRAIN_GOALS", "").split(",") if g.strip()],
        "production_enabled": os.getenv("FACTORY_ALLOW_PRODUCTION", "0") == "1",
        "youtube_publish_enabled": os.getenv("FACTORY_ALLOW_YOUTUBE_PUBLISH", "0") == "1",
        "private_network_block": os.getenv("BRAIN_BLOCK_PRIVATE_NETWORKS", "1") == "1",
        "uptime_seconds": round(time.time() - STARTED, 1),
    })


@app.get("/v1/fingerprint", dependencies=[Depends(require_auth)])
def fingerprint():
    value = os.getenv("BRAIN_INSTANCE_ID", "brain")
    return {"instance": hashlib.sha256(value.encode()).hexdigest()[:16]}

"""Minimal authenticated control/health API for the Brain runtime.

No arbitrary shell, credential, or filesystem control is exposed here.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException\nfrom pydantic import BaseModel\nimport subprocess\nimport threading
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




FILM_JOBS = STATE / "film_jobs"
FILM_JOBS.mkdir(parents=True, exist_ok=True)

class FilmRequest(BaseModel):
    title: str
    target_minutes: int = 12
    language: str = "ar"

def _job_path(job_id: str) -> Path:
    return FILM_JOBS / (job_id + ".json")

def _save_job(job: dict) -> None:
    tmp = _job_path(job["id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_job_path(job["id"]))

def _run_film_job(job_id: str, body: FilmRequest) -> None:
    log_path = FILM_JOBS / (job_id + ".log")
    job = {"id": job_id, "status": "RUNNING", "title": body.title,
           "target_minutes": body.target_minutes, "language": body.language}
    _save_job(job)
    env = os.environ.copy()
    env["FACTORY_ONE_SHOT"] = "1"
    env["FACTORY_ALLOW_PRODUCTION"] = "1"
    env["FACTORY_REQUIRE_REAL_MEDIA"] = "1"
    env["FACTORY_DURATION_SECONDS"] = str(max(1, min(600, body.target_minutes * 60)))
    env["FACTORY_TOPICS_JSON"] = json.dumps([{
        "title": body.title,
        "objective": body.title,
        "language": body.language,
        "route": "cinematic"
    }], ensure_ascii=False)
    env["FACTORY_OBJECTIVE"] = "Produce and verify the requested cinematic film: " + body.title
    try:
        with open(log_path, "a", encoding="utf-8") as log:
            p = subprocess.Popen(
                ["python", "-m", "brain_v7.braincore_v2.background_factory_worker"],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            rc = p.wait()
        job["status"] = "COMPLETED" if rc == 0 else "FAILED"
        job["return_code"] = rc
        job["log"] = str(log_path.relative_to(STATE))
        job["output_dir"] = os.getenv("FACTORY_OUTPUT_DIR", "cinematic_output")
    except Exception as exc:
        job["status"] = "FAILED"
        job["error"] = f"{type(exc).__name__}: {exc}"
    _save_job(job)

@app.post("/v1/films", dependencies=[Depends(require_auth)])
def create_film(body: FilmRequest):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if body.target_minutes < 1 or body.target_minutes > 30:
        raise HTTPException(status_code=400, detail="target_minutes must be 1..30")
    for p in FILM_JOBS.glob("*.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            if j.get("status") == "RUNNING":
                return JSONResponse({"ok": False, "status": "BUSY", "active_job": j}, status_code=409)
        except Exception:
            pass
    import uuid
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "status": "QUEUED", "title": title,
           "target_minutes": body.target_minutes, "language": body.language}
    _save_job(job)
    threading.Thread(target=_run_film_job, args=(job_id, body), daemon=True).start()
    return {"ok": True, "job": job, "profile": "CINEMATIC V3 PRO"}

@app.get("/v1/films/{job_id}", dependencies=[Depends(require_auth)])
def film_status(job_id: str):
    path = _job_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="film job not found")
    return {"ok": True, "job": json.loads(path.read_text(encoding="utf-8"))}

@app.get("/v1/fingerprint", dependencies=[Depends(require_auth)])
def fingerprint():
    value = os.getenv("BRAIN_INSTANCE_ID", "brain")
    return {"instance": hashlib.sha256(value.encode()).hexdigest()[:16]}

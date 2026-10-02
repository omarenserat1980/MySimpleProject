"""Authenticated BRAIN Cloud Hub control plane."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from cloud.deploy_engine import DeployError, deploy, docker_available, logs, restart, status as docker_status, stop
from cloud.runtime_orchestrator import CloudRuntime

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv("BRAIN_STATE_DIR", str(ROOT / ".brain_state")))
STARTED = time.time()
TOKEN = os.getenv("BRAIN_CONTROL_TOKEN", "")
app = FastAPI(title="BRAIN Cloud Hub", docs_url=None, redoc_url=None)
runtime = CloudRuntime()

# The Cloud Hub owns its queue worker. No Termux/external process is required.
if os.getenv("BRAIN_API_QUEUE_WORKER", "1").strip().lower() in {"1", "true", "yes", "on"}:
    threading.Thread(target=runtime.run_forever, name="brain-cloud-queue", daemon=True).start()

FILM_JOBS = STATE / "film_jobs"
FILM_JOBS.mkdir(parents=True, exist_ok=True)


def require_auth(
    request: Request,
    authorization: str | None = Header(default=None),
    local_app: str | None = Header(default=None, alias="X-BRAIN-Local-App"),
) -> None:
    # Local Android control is allowed only over loopback with an explicit marker.
    host = request.client.host if request.client else ""
    if local_app == "1" and host in {"127.0.0.1", "::1", "localhost"}:
        return
    if not TOKEN:
        raise HTTPException(status_code=503, detail="control plane token is not configured")
    expected = "Bearer " + TOKEN
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="unauthorized")




CUSTOMER_REQUESTS = STATE / "customer_requests"
CUSTOMER_REQUESTS.mkdir(parents=True, exist_ok=True)


class CustomerRequest(BaseModel):
    display_name: str
    service: str
    need: str
    customer_type: str = "INDIVIDUAL"
    legal_entity_name: str | None = None
    registration_id: str | None = None
    authorized_representative: str | None = None
    marketing_consent: bool = False


class CustomerMessage(BaseModel):
    message: str
    channel: str = "BRAIN_PORTAL"
    purpose: str = "SERVICE"


def _customer_path(request_id: str) -> Path:
    safe = request_id.strip()
    if not safe or "/" in safe or "\\" in safe or safe in {".", ".."}:
        raise HTTPException(status_code=400, detail="invalid request_id")
    return CUSTOMER_REQUESTS / (safe + ".json")


def _save_customer(record: dict) -> None:
    CUSTOMER_REQUESTS.mkdir(parents=True, exist_ok=True)
    tmp = _customer_path(record["request_id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_customer_path(record["request_id"]))


def _load_customer(request_id: str) -> dict:
    path = _customer_path(request_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="customer request not found")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="customer request state is unreadable") from exc


def _customer_audit(record: dict, event: str, **details: object) -> None:
    record.setdefault("audit", []).append({"event": event, "at": time.time(), **details})


@app.post("/api/customers")
def create_customer(body: CustomerRequest):
    display_name, service, need = body.display_name.strip(), body.service.strip(), body.need.strip()
    allowed_types = {"INDIVIDUAL", "SOLE_PROPRIETOR", "COMPANY", "ORGANIZATION", "GOVERNMENT", "PARTNER"}
    entity_types = {"COMPANY", "ORGANIZATION", "GOVERNMENT"}
    customer_type = body.customer_type.strip().upper()
    if customer_type not in allowed_types:
        raise HTTPException(status_code=400, detail="unsupported customer_type")
    if not display_name or not service or not need:
        raise HTTPException(status_code=400, detail="display_name, service and need are required")
    request_id = str(uuid.uuid4())
    record = {
        "request_id": request_id,
        "display_name": display_name,
        "customer_type": customer_type,
        "legal_entity": {
            "is_entity": customer_type in entity_types,
            "legal_entity_name": (body.legal_entity_name or display_name).strip() if customer_type in entity_types else None,
            "registration_id": body.registration_id.strip() if body.registration_id else None,
            "authorized_representative": body.authorized_representative.strip() if body.authorized_representative else None,
            "verification_state": "REQUIRED" if customer_type in entity_types else "NOT_APPLICABLE",
        },
        "service": service,
        "need": need,
        "consent": {
            "service": True,
            "marketing": bool(body.marketing_consent),
            "marketing_source": "customer_portal" if body.marketing_consent else None,
        },
        "status": "READY_FOR_REVIEW",
        "lifecycle_state": "DISCOVERED",
        "pipeline_state": "DISCOVERED",
        "evidence_state": "READY_FOR_REVIEW",
        "financial_state": "NOT_VERIFIED",
        "revenue_state": "NOT_REALIZED",
        "external_actions": [],
        "audit": [],
        "created_at": time.time(),
    }
    _customer_audit(record, "CUSTOMER_REQUEST_CREATED",
                     lifecycle_state="DISCOVERED",
                     marketing_consent=bool(body.marketing_consent))
    _save_customer(record)
    return {
        "ok": True,
        "request_id": request_id,
        "status": record["status"],
        "lifecycle_state": record["lifecycle_state"],
        "consent_state": record["consent"],
        "evidence_state": record["evidence_state"],
        "financial_state": record["financial_state"],
        "revenue_state": record["revenue_state"],
    }


@app.get("/api/customers/{request_id}")
def get_customer(request_id: str):
    return {"ok": True, "customer": _load_customer(request_id)}


@app.post("/api/customers/{request_id}/approve", dependencies=[Depends(require_auth)])
def approve_customer(request_id: str):
    record = _load_customer(request_id)
    if record["lifecycle_state"] not in {"DISCOVERED", "READY_FOR_REVIEW"}:
        raise HTTPException(status_code=409, detail="customer request is not awaiting approval")
    record["status"] = "APPROVED"
    record["lifecycle_state"] = "APPROVED"
    record["pipeline_state"] = "APPROVED"
    _customer_audit(record, "HUMAN_APPROVAL_RECORDED", lifecycle_state="APPROVED")
    _save_customer(record)
    return {"ok": True, "customer": record}


@app.post("/api/customers/{request_id}/message", dependencies=[Depends(require_auth)])
def message_customer(request_id: str, body: CustomerMessage):
    record = _load_customer(request_id)
    from brain_v12.business.customer_governance import (
        COMMUNICATION_CHANNELS, CONSENT_PURPOSES, Consent,
        CustomerOperation, CustomerProfile,
    )
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="message is required")
    if body.channel not in COMMUNICATION_CHANNELS:
        raise HTTPException(status_code=400, detail="unsupported communication channel")
    if body.purpose not in CONSENT_PURPOSES:
        raise HTTPException(status_code=400, detail="unsupported consent purpose")
    profile = CustomerProfile(
        customer_id=record["request_id"],
        display_name=record["display_name"],
        consents=[
            Consent(purpose="SERVICE", granted=bool(record["consent"]["service"]), source="customer_portal"),
            Consent(purpose="MARKETING", granted=bool(record["consent"]["marketing"]), source="customer_portal"),
        ],
    )
    decision = CustomerOperation(
        customer_id=record["request_id"], action="SEND_MESSAGE",
        channel=body.channel, purpose=body.purpose,
    ).authorize(profile)
    if decision.get("status") != "REQUIRES_AUTHORIZATION":
        return {"ok": False, "gate": decision}
    _customer_audit(record, "EXTERNAL_MESSAGE_AUTHORIZED",
                     channel=body.channel, purpose=body.purpose)
    record["external_actions"].append({
        "action": "SEND_MESSAGE", "channel": body.channel, "purpose": body.purpose,
        "message": body.message.strip(), "status": "AUTHORIZED_NOT_SENT", "at": time.time(),
    })
    _save_customer(record)
    return {
        "ok": True,
        "gate": "AUTHORIZED_NOT_SENT",
        "message": "Connector execution remains a separate external action.",
        "customer": record,
    }


@app.get("/api/customers/{request_id}/financial", dependencies=[Depends(require_auth)])
def customer_financial_state(request_id: str):
    record = _load_customer(request_id)
    return {
        "ok": True,
        "request_id": request_id,
        "financial_state": record["financial_state"],
        "revenue_state": record["revenue_state"],
        "source": "customer_portal",
        "payment_verification": "REVENUE_LEDGER_ONLY",
    }


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
        "service": "BRAIN Cloud Hub",
        "mode": os.getenv("BRAIN_CLOUD_MODE", "internet-connected"),
        "role": "brain_cloud_native",
        "runtime_mode": "cloud_only",
        "device_required": False,
        "termux_dependency": False,
        "goals": [g.strip() for g in os.getenv("BRAIN_GOALS", "").split(",") if g.strip()],
        "production_enabled": os.getenv("FACTORY_ALLOW_PRODUCTION", "0") == "1",
        "youtube_publish_enabled": os.getenv("FACTORY_ALLOW_YOUTUBE_PUBLISH", "0") == "1",
        "cloud_runtime": runtime.snapshot(),
        "private_network_block": os.getenv("BRAIN_BLOCK_PRIVATE_NETWORKS", "1") == "1",
        "docker_executor_available": docker_available(),
        "uptime_seconds": round(time.time() - STARTED, 1),
    })


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


def _find_final_video(job: dict) -> Path | None:
    recorded = job.get("video_path")
    if recorded:
        path = Path(str(recorded))
        if path.is_file() and path.stat().st_size >= 1024:
            return path
    configured = job.get("output_dir") or os.getenv("FACTORY_OUTPUT_DIR", "cinematic_output")
    output_dir = Path(configured)
    if not output_dir.is_absolute():
        output_dir = Path(__file__).resolve().parents[1] / output_dir
    if not output_dir.is_dir():
        return None
    exact = output_dir / "final.mp4"
    return exact if exact.is_file() and exact.stat().st_size >= 1024 else None


def _run_film_job(job_id: str, body: FilmRequest) -> None:
    """Compatibility worker: enqueue into the single CloudRuntime production path."""
    job = runtime.enqueue("cinematic", {
        "title": body.title.strip(),
        "target_minutes": body.target_minutes,
        "language": body.language,
        "publish_youtube": False,
        "legacy_job_id": job_id,
    })
    legacy = {"id": job_id, "status": "QUEUED", "runtime_job_id": job["id"], "route": "cloud_runtime"}
    _save_job(legacy)


@app.post("/v1/films", dependencies=[Depends(require_auth)])
def create_film(body: FilmRequest):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    if body.target_minutes < 1 or body.target_minutes > 30:
        raise HTTPException(status_code=400, detail="target_minutes must be 1..30")
    job = runtime.enqueue("cinematic", {
        "title": title,
        "target_minutes": body.target_minutes,
        "language": body.language,
        "publish_youtube": False,
    })
    return {"ok": True, "job": job, "profile": "CINEMATIC V3 PRO", "runtime": "brain_cloud"}


class CinematicAutopilotRequest(BaseModel):
    max_attempts: int = 3


@app.post("/v1/cinematic/autopilot", dependencies=[Depends(require_auth)])
def cinematic_autopilot(body: CinematicAutopilotRequest):
    attempts = max(1, min(5, int(body.max_attempts)))
    job = runtime.enqueue("cinematic_autopilot", {"max_attempts": attempts})
    return {"ok": True, "job": job, "profile": "BRAIN CLOUD CINEMATIC AUTOPILOT",
            "runtime": "brain_cloud", "device_required": False, "termux_required": False}


@app.get("/v1/films", dependencies=[Depends(require_auth)])
def list_films(limit: int = 50):
    return {"ok": True, "jobs": runtime.list(limit)}


@app.get("/v1/films/{job_id}", dependencies=[Depends(require_auth)])
def film_status(job_id: str):
    job = runtime.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="film job not found")
    return {"ok": True, "job": job}


@app.get("/v1/films/{job_id}/video", dependencies=[Depends(require_auth)])
def legacy_film_video(job_id: str):
    path = _job_path(job_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="film job not found")
    job = json.loads(path.read_text(encoding="utf-8"))
    if job.get("status") not in {"COMPLETED", "VERIFIED_COMPLETED"}:
        raise HTTPException(status_code=409, detail="film is not verified complete")
    video = _find_final_video(job)
    if not video:
        raise HTTPException(status_code=404, detail="verified film output not found")
    return FileResponse(video, media_type="video/mp4", filename=video.name)


@app.post("/v1/films/{job_id}/publish", dependencies=[Depends(require_auth)])
def publish_film(job_id: str):
    job = runtime.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="film job not found")
    if job["stage"] != "ready":
        raise HTTPException(status_code=409, detail="film is not ready for publication")
    result = job.get("result", {})
    verification = result.get("verification", {})
    video_path = verification.get("video_path") or result.get("video_path")
    if not video_path:
        raise HTTPException(status_code=409, detail="verified video path is missing")
    publish_job = runtime.enqueue("youtube_publish", {
        "video_path": video_path,
        "title": job["payload"].get("title", "Brain Cloud Video"),
        "description": job["payload"].get("description", ""),
        "tags": job["payload"].get("tags", []),
        "privacy": job["payload"].get("privacy", "private"),
    })
    return {"ok": True, "job": publish_job, "executor": "cloud_youtube_executor"}


@app.get("/v1/runtime", dependencies=[Depends(require_auth)])
def runtime_status():
    return runtime.snapshot()


@app.get("/v1/agents", dependencies=[Depends(require_auth)])
def agents_status():
    return {"ok": True, "agents": runtime.snapshot().get("agents", []), "runtime": "brain_cloud"}


@app.get("/v1/storage", dependencies=[Depends(require_auth)])
def storage_status():
    snap = runtime.snapshot()
    storage = snap["storage"]
    media = Path(storage["media_dir"])
    files = []
    if media.is_dir():
        for p in sorted(media.rglob("*")):
            if p.is_file():
                files.append({"path": str(p), "size": p.stat().st_size})
    return {"ok": True, "runtime": "brain_cloud", "storage": storage, "files": files[:500]}




@app.get("/v1/fingerprint", dependencies=[Depends(require_auth)])
def fingerprint():
    value = os.getenv("BRAIN_INSTANCE_ID", "brain")
    return {"instance": hashlib.sha256(value.encode()).hexdigest()[:16]}


class DeployRequest(BaseModel):
    name: str
    image: str
    port: int = 8000


def _service_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name.strip())
    if not safe or safe in {".", ".."}:
        raise HTTPException(status_code=400, detail="invalid service name")
    return STATE / "services" / (safe + ".json")


def _save_service(service: dict) -> None:
    services_dir = STATE / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    _service_path(service["name"]).write_text(
        json.dumps(service, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@app.get("/v1/platform", dependencies=[Depends(require_auth)])
def platform():
    return {
        "service": "BRAIN Cloud Hub",
        "role": "brain_cloud_native",
        "paid_render_dependency": False,
        "capabilities": ["services", "deploy", "restart", "logs", "health", "film_jobs", "ffmpeg", "qc"],
        "runtime_mode": "cloud_only",
        "device_required": False,
        "termux_dependency": False,
        "executor": "local_docker" if os.getenv("BRAIN_DEPLOY_EXECUTOR", "none") == "local_docker" else "disabled",
    }


@app.get("/v1/services", dependencies=[Depends(require_auth)])
def services():
    services_dir = STATE / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for p in sorted(services_dir.glob("*.json")):
        try:
            item = json.loads(p.read_text(encoding="utf-8"))
            if item.get("name"):
                item["runtime"] = docker_status(item["name"]) if docker_available() else {"status": "DOCKER_UNAVAILABLE"}
            items.append(item)
        except Exception:
            continue
    return {"ok": True, "services": items}


@app.post("/v1/services", dependencies=[Depends(require_auth)])
def register_service(body: DeployRequest):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="name is required")
    if not body.image.strip():
        raise HTTPException(status_code=400, detail="image is required")
    if body.port < 1 or body.port > 65535:
        raise HTTPException(status_code=400, detail="invalid port")
    service = {
        "name": body.name.strip(),
        "image": body.image.strip(),
        "port": body.port,
        "status": "REGISTERED",
    }
    _save_service(service)
    return {"ok": True, "service": service}


@app.post("/v1/services/{name}/deploy", dependencies=[Depends(require_auth)])
def deploy_service(name: str):
    path = _service_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="service not registered")
    service = json.loads(path.read_text(encoding="utf-8"))
    if os.getenv("BRAIN_DEPLOY_EXECUTOR", "none") != "local_docker":
        raise HTTPException(status_code=503, detail="local Docker executor is disabled")
    try:
        runtime = deploy(name=service["name"], image=service["image"], port=int(service["port"]))
    except DeployError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    service["status"] = "DEPLOYED"
    service["runtime"] = runtime
    _save_service(service)
    return {"ok": True, "service": service}


@app.get("/v1/services/{name}", dependencies=[Depends(require_auth)])
def service_status(name: str):
    path = _service_path(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="service not registered")
    service = json.loads(path.read_text(encoding="utf-8"))
    service["runtime"] = docker_status(service["name"]) if docker_available() else {"status": "DOCKER_UNAVAILABLE"}
    return {"ok": True, "service": service}


@app.post("/v1/services/{name}/restart", dependencies=[Depends(require_auth)])
def restart_service(name: str):
    try:
        runtime = restart(name)
    except DeployError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"ok": True, "runtime": runtime}


@app.post("/v1/services/{name}/stop", dependencies=[Depends(require_auth)])
def stop_service(name: str):
    try:
        runtime = stop(name)
    except DeployError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {"ok": True, "runtime": runtime}


@app.get("/v1/services/{name}/logs", dependencies=[Depends(require_auth)])
def service_logs(name: str, tail: int = 200):
    try:
        return {"ok": True, **logs(name, tail=tail)}
    except DeployError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

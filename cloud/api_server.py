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
from dataclasses import asdict
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from cloud.deploy_engine import DeployError, deploy, docker_available, logs, restart, status as docker_status, stop
from cloud.runtime_orchestrator import CloudRuntime
from cloud.approval_desk import create_approval, decide_approval, get_approval, list_approvals, notification_status
from cloud.customer_communications import Channel, CommunicationHub, MessageState
from cloud.diwan import CaseFile, Correspondence, CorrespondenceState, RoutingAssignment, RecordState, archive_eligible, register_number
from cloud.brain_fabric_api import router as fabric_router\nfrom brain_v12.business.customer_activity_supervisor import CustomerActivitySupervisor

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv("BRAIN_STATE_DIR", str(ROOT / ".brain_state")))
STARTED = time.time()
TOKEN = os.getenv("BRAIN_CONTROL_TOKEN", "")
app = FastAPI(title="BRAIN Cloud Hub", docs_url=None, redoc_url=None)
runtime = CloudRuntime()
COMMUNICATION_HUB = CommunicationHub(STATE / "customer_communications")
app.include_router(fabric_router)

# The Cloud Hub owns its queue worker. No Termux/external process is required.
if os.getenv("BRAIN_API_QUEUE_WORKER", "1").strip().lower() in {"1", "true", "yes", "on"}:
    threading.Thread(target=runtime.run_forever, name="brain-cloud-queue", daemon=True).start()

FILM_JOBS = STATE / "film_jobs"
FILM_JOBS.mkdir(parents=True, exist_ok=True)

FEEDBACK_STATE = STATE / "customer_feedback"
FEEDBACK_STATE.mkdir(parents=True, exist_ok=True)

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


from cloud.customer_feedback import FeedbackState, FeedbackStore
FEEDBACK_STORE = FeedbackStore(STATE)


CUSTOMER_REQUESTS = STATE / "customer_requests"
CUSTOMER_REQUESTS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PUBLIC CLIENT ACCOUNTS / 5-DAY TRIAL
# The trial is server-side and tied to a normalized email address. The client
# UI is never trusted to decide eligibility.
# ---------------------------------------------------------------------------
CLIENT_ACCOUNTS = STATE / "client_accounts"
CLIENT_ACCOUNTS.mkdir(parents=True, exist_ok=True)
CLIENT_SESSIONS = STATE / "client_sessions"
CLIENT_SESSIONS.mkdir(parents=True, exist_ok=True)
TRIAL_SECONDS = 5 * 24 * 60 * 60

def _email_key(email: str) -> str:
    value = email.strip().lower()
    if "@" not in value or len(value) > 254:
        raise HTTPException(status_code=400, detail="valid email is required")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _account_path(email: str) -> Path:
    return CLIENT_ACCOUNTS / (_email_key(email) + ".json")

def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if len(password) < 10:
        raise HTTPException(status_code=400, detail="password must be at least 10 characters")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000)
    return salt.hex(), digest.hex()

def _verify_password(password: str, account: dict) -> bool:
    try:
        salt = bytes.fromhex(account["password_salt"])
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000).hex()
        return hmac.compare_digest(digest, account["password_hash"])
    except (KeyError, ValueError):
        return False

def _save_account(account: dict) -> None:
    tmp = _account_path(account["email"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(account, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_account_path(account["email"]))

def _load_account(email: str) -> dict | None:
    path = _account_path(email)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=500, detail="account state is unreadable")

def _create_client_session(email: str) -> str:
    raw = uuid.uuid4().hex + uuid.uuid4().hex
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    record = {"email": email.strip().lower(), "expires_at": time.time() + 24 * 60 * 60}
    (CLIENT_SESSIONS / (token_hash + ".json")).write_text(json.dumps(record), encoding="utf-8")
    return raw

def _client_account_from_token(request: Request) -> dict:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="login required")
    raw = header[7:].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="login required")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    path = CLIENT_SESSIONS / (token_hash + ".json")
    if not path.exists():
        raise HTTPException(status_code=401, detail="session expired")
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="invalid session")
    if float(session.get("expires_at", 0)) <= time.time():
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=401, detail="session expired")
    account = _load_account(session["email"])
    if not account:
        raise HTTPException(status_code=401, detail="account unavailable")
    return account

class ClientAuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(default="", max_length=120)

class ClientOrderRequest(BaseModel):
    service: str
    plan: str
    need: str = Field(min_length=10, max_length=10000)


@app.post("/api/payments/paytabs/callback")
async def paytabs_callback(request: Request):
    """Public PayTabs callback; verify HMAC before changing payment state."""
    from brain.provider_hub.paytabs_webhook import parse_and_validate_payment
    raw_body = await request.body()
    signature = request.headers.get("Signature", "")
    server_key = os.getenv("PAYTABS_SERVER_KEY", "").strip()
    if not server_key:
        raise HTTPException(status_code=503, detail="payment provider secret is not configured")
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        order_id = str(payload.get("cart_id", ""))
        amount = str(payload.get("cart_amount", ""))
        currency = str(payload.get("cart_currency", ""))
        verified = parse_and_validate_payment(raw_body, signature, server_key, expected_order_id=order_id, expected_amount=amount, expected_currency=currency)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    evidence_dir = STATE / "payment_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    tran_ref = str(verified["tran_ref"])
    evidence_path = evidence_dir / (hashlib.sha256(tran_ref.encode()).hexdigest() + ".json")
    if evidence_path.exists():
        return {"ok": True, "status": "ALREADY_RECORDED", "tran_ref": tran_ref}
    record = {"provider":"paytabs","order_id":order_id,"tran_ref":tran_ref,"amount":amount,"currency":currency,"verified_at":time.time(),"payment_state":"PAYMENT_VERIFIED","evidence":verified}
    evidence_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "status": "PAYMENT_VERIFIED", "tran_ref": tran_ref}

@app.post("/api/auth/register")
def client_register(body: ClientAuthRequest):
    email = body.email.strip().lower()
    existing = _load_account(email)
    if existing:
        # Deliberately generic: do not reveal account existence.
        raise HTTPException(status_code=409, detail="account cannot be created with these credentials")
    salt, password_hash = _hash_password(body.password)
    now = time.time()
    account = {
        "client_id": str(uuid.uuid4()),
        "email": email,
        "display_name": body.display_name.strip() or email.split("@")[0],
        "password_salt": salt,
        "password_hash": password_hash,
        "created_at": now,
        "trial": {"eligible": True, "started_at": now, "duration_seconds": TRIAL_SECONDS,
                  "used": True, "state": "TRIAL_ACTIVE"},
        "orders": [],
        "audit": [{"event": "ACCOUNT_CREATED_AND_TRIAL_STARTED", "at": now}],
    }
    _save_account(account)
    token = _create_client_session(email)
    return {"ok": True, "token": token, "account": _client_public(account)}

@app.post("/api/auth/login")
def client_login(body: ClientAuthRequest):
    account = _load_account(body.email)
    if not account or not _verify_password(body.password, account):
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = _create_client_session(account["email"])
    return {"ok": True, "token": token, "account": _client_public(account)}

def _client_public(account: dict) -> dict:
    trial = dict(account["trial"])
    remaining = max(0, int(trial["started_at"] + trial["duration_seconds"] - time.time()))
    trial["remaining_seconds"] = remaining
    trial["remaining_days"] = round(remaining / 86400, 2)
    trial["state"] = "TRIAL_ACTIVE" if remaining > 0 else "TRIAL_EXPIRED"
    return {"client_id": account["client_id"], "email": account["email"],
            "display_name": account["display_name"], "trial": trial,
            "orders": account.get("orders", [])}

# ---------------------------------------------------------------------------
# AUTHORIZED CUSTOMER ACTIVITY REPORT + CONTINUATION
# Cross-customer visibility is intentionally restricted to the Brain control
# plane. A customer session may access only its own account/orders.
# ---------------------------------------------------------------------------
CUSTOMER_ACTIVITY_SUPERVISOR = CustomerActivitySupervisor(STATE)

@app.get("/api/brain/customers/activity-report", dependencies=[Depends(require_auth)])
def brain_customer_activity_report(include_completed: bool = True):
    """Return the current customer/activity inventory for an authorized operator."""
    return CUSTOMER_ACTIVITY_SUPERVISOR.report(include_completed=include_completed)


@app.post("/api/brain/customers/activity-continue", dependencies=[Depends(require_auth)])
def brain_customer_activity_continue(customer_id: str | None = None, limit: int = 50):
    """Inspect unfinished activities and continue them through an injected executor.

    The executor must return completed=True plus structured verification:
    passed=True, a non-empty criterion, and evidence. Without that proof the
    activity remains incomplete.
    """
    return CUSTOMER_ACTIVITY_SUPERVISOR.continue_unfinished(customer_id=customer_id, limit=limit)


@app.get("/api/auth/me")
def client_me(request: Request):
    return {"ok": True, "account": _client_public(_client_account_from_token(request))}

@app.get("/api/trial")
def client_trial(request: Request):
    account = _client_account_from_token(request)
    return {"ok": True, "trial": _client_public(account)["trial"]}

@app.post("/api/orders")
def client_order(request: Request, body: ClientOrderRequest):
    account = _client_account_from_token(request)
    public = _client_public(account)
    if public["trial"]["state"] != "TRIAL_ACTIVE" and body.plan.upper().startswith("FREE TRIAL"):
        raise HTTPException(status_code=409, detail="free trial has expired")
    order_id = "BRAIN-CLIENT-" + time.strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8].upper()
    order = {"order_id": order_id, "service": body.service.strip(), "plan": body.plan.strip(),
             "need": body.need.strip(), "state": "TRIAL_REQUESTED" if body.plan.upper().startswith("FREE TRIAL") else "NEW",
             "created_at": time.time(), "payment_state": "NOT_REQUIRED_TRIAL" if body.plan.upper().startswith("FREE TRIAL") else "PAYMENT_PENDING"}
    account.setdefault("orders", []).append(order)
    account.setdefault("audit", []).append({"event": "SERVICE_ORDER_CREATED", "order_id": order_id, "at": time.time()})
    _save_account(account)
    return {"ok": True, "order": order, "account": _client_public(account)}


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
    msg = COMMUNICATION_HUB.create(
        customer_id=record["request_id"],
        channel=Channel.EMAIL if body.channel == "EMAIL" else (
            Channel.WEB_CHAT if body.channel == "WEB_CHAT" else Channel.CUSTOMER_PORTAL
        ),
        direction="OUTBOUND",
        body=body.message.strip(),
        consent_scope=body.purpose,
        case_id=record.get("case_id"),
        idempotency_key=f"customer:{record['request_id']}:outbound:{hashlib.sha256(body.message.strip().encode()).hexdigest()}",
    )
    record["external_actions"].append({
        "action": "SEND_MESSAGE", "channel": body.channel, "purpose": body.purpose,
        "message_id": msg.message_id, "message": body.message.strip(),
        "status": "QUEUED_FOR_CONNECTOR", "at": time.time(),
    })
    _save_customer(record)
    return {
        "ok": True,
        "gate": "QUEUED_FOR_CONNECTOR",
        "message_id": msg.message_id,
        "message": "Message is recorded in the Communications Hub and awaits a configured transport connector.",
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


class ApprovalCreateRequest(BaseModel):
    subject: str
    reason: str
    risk: str = "MEDIUM"
    requested_action: str = "APPROVE"
    recipient_email: str | None = None
    evidence: list[dict] = Field(default_factory=list)
    source_type: str = "BRAIN"
    source_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    decision: str
    actor: str
    note: str = ""


@app.get("/v1/diwan/approvals", dependencies=[Depends(require_auth)])
def diwan_approvals(status_filter: str = "PENDING", limit: int = 100):
    return {"ok": True, "system": "BRAIN_DIWAN", "approvals": list_approvals(status_filter, limit)}


@app.get("/v1/diwan/approvals/{approval_id}", dependencies=[Depends(require_auth)])
def diwan_approval(approval_id: str):
    approval = get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="approval not found")
    return {"ok": True, "system": "BRAIN_DIWAN", "approval": approval}


@app.post("/v1/diwan/approvals", dependencies=[Depends(require_auth)])
def create_diwan_approval(body: ApprovalCreateRequest):
    if not body.subject.strip() or not body.reason.strip():
        raise HTTPException(status_code=400, detail="subject and reason are required")
    approval = create_approval(
        subject=body.subject,
        reason=body.reason,
        risk=body.risk,
        requested_action=body.requested_action,
        recipient_email=body.recipient_email,
        evidence=body.evidence,
        source_type=body.source_type,
        source_id=body.source_id,
        metadata=body.metadata,
    )
    return {"ok": True, "system": "BRAIN_DIWAN", "approval": approval}


@app.post("/v1/diwan/approvals/{approval_id}/decision", dependencies=[Depends(require_auth)])
def decide_diwan_approval(approval_id: str, body: ApprovalDecisionRequest):
    try:
        approval = decide_approval(
            approval_id,
            decision=body.decision,
            actor=body.actor,
            note=body.note,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        detail = str(exc)
        status_code = 422 if detail.startswith("invalid transition") or "requires evidence_ref" in detail else 409
        raise HTTPException(status_code=status_code, detail=detail)
    return {"ok": True, "system": "BRAIN_DIWAN", "approval": approval}


@app.get("/v1/diwan/notifications", dependencies=[Depends(require_auth)])
def diwan_notifications(limit: int = 100):
    return {"ok": True, "system": "BRAIN_DIWAN", "notifications": notification_status(limit)}

def now_iso() -> str:
    return __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# BRAIN DIWAN & SECRETARIAT OS — canonical registry / cases / correspondence / archive
# ---------------------------------------------------------------------------
DIWAN_CASES = STATE / "diwan_cases"
DIWAN_CORRESPONDENCE = STATE / "diwan_correspondence"

def _diwan_store(root: Path, key: str, value: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    tmp=root/(key+".tmp"); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(root/(key+".json"))
def _diwan_load(root: Path, key: str) -> dict|None:
    p=root/(key+".json")
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
def _diwan_next_number(prefix: str, root: Path) -> str:
    root.mkdir(parents=True,exist_ok=True)
    return register_number(prefix,len(list(root.glob("*.json")))+1)

class DiwanCorrespondenceRequest(BaseModel):
    direction:str
    subject:str
    channel:str
    sender:str|None=None
    recipients:list[str]=Field(default_factory=list)
    case_id:str|None=None
    classification:str="UNCLASSIFIED"
    confidentiality:str="INTERNAL"
    content_ref:str|None=None
    attachments:list[str]=Field(default_factory=list)
class DiwanCaseRequest(BaseModel):
    title:str
    owner_type:str
    owner_id:str
class DiwanTransitionRequest(BaseModel):
    state:str
    actor:str
    reason:str=""
class DiwanRouteRequest(BaseModel):
    target:str
    assigned_by:str
    deadline_at:str|None=None
    notes:str=""

@app.post("/v1/diwan/correspondence",dependencies=[Depends(require_auth)])
def diwan_register_correspondence(body:DiwanCorrespondenceRequest):
    direction=body.direction.upper().strip()
    if direction not in {"INBOUND","OUTBOUND"}: raise HTTPException(400,"direction must be INBOUND or OUTBOUND")
    if not body.subject.strip() or not body.channel.strip(): raise HTTPException(400,"subject and channel are required")
    c=Correspondence(direction=direction,subject=body.subject.strip(),channel=body.channel.strip().upper(),sender=body.sender,recipients=body.recipients,case_id=body.case_id,classification=body.classification,confidentiality=body.confidentiality,content_ref=body.content_ref,attachments=body.attachments,number=_diwan_next_number("IN" if direction=="INBOUND" else "OUT",DIWAN_CORRESPONDENCE))
    c.transition(CorrespondenceState.REGISTERED,"diwan")
    record={k:(v.value if hasattr(v,"value") else v) for k,v in c.__dict__.items()}
    _diwan_store(DIWAN_CORRESPONDENCE,c.correspondence_id,{"record":record})
    return {"ok":True,"system":"BRAIN_DIWAN","correspondence":record}

@app.get("/v1/diwan/correspondence",dependencies=[Depends(require_auth)])
def diwan_list_correspondence(limit:int=100):
    items=[]
    for p in sorted(DIWAN_CORRESPONDENCE.glob("*.json"),reverse=True)[:max(1,min(limit,500))]:
        try: items.append(json.loads(p.read_text(encoding="utf-8"))["record"])
        except Exception: continue
    return {"ok":True,"system":"BRAIN_DIWAN","correspondence":items}

@app.get("/v1/diwan/correspondence/{correspondence_id}",dependencies=[Depends(require_auth)])
def diwan_get_correspondence(correspondence_id:str):
    item=_diwan_load(DIWAN_CORRESPONDENCE,correspondence_id)
    if not item: raise HTTPException(404,"correspondence not found")
    return {"ok":True,"system":"BRAIN_DIWAN","correspondence":item["record"]}

@app.post("/v1/diwan/correspondence/{correspondence_id}/transition",dependencies=[Depends(require_auth)])
def diwan_transition_correspondence(correspondence_id:str,body:DiwanTransitionRequest):
    item=_diwan_load(DIWAN_CORRESPONDENCE,correspondence_id)
    if not item: raise HTTPException(404,"correspondence not found")
    record=item["record"]; c=Correspondence(**{**record,"state":CorrespondenceState(record["state"])})
    try: c.transition(CorrespondenceState(body.state),body.actor,body.reason)
    except (ValueError,KeyError) as exc: raise HTTPException(409,str(exc))
    item["record"]={k:(v.value if hasattr(v,"value") else v) for k,v in c.__dict__.items()}
    _diwan_store(DIWAN_CORRESPONDENCE,correspondence_id,item)
    return {"ok":True,"system":"BRAIN_DIWAN","correspondence":item["record"]}

@app.post("/v1/diwan/cases",dependencies=[Depends(require_auth)])
def diwan_create_case(body:DiwanCaseRequest):
    case=CaseFile(title=body.title.strip(),owner_type=body.owner_type,owner_id=body.owner_id); case.number=_diwan_next_number("CASE",DIWAN_CASES)
    data=dict(case.__dict__); _diwan_store(DIWAN_CASES,case.case_id,data)
    return {"ok":True,"system":"BRAIN_DIWAN","case":data}

@app.get("/v1/diwan/cases",dependencies=[Depends(require_auth)])
def diwan_list_cases(limit:int=100):
    items=[]
    for p in sorted(DIWAN_CASES.glob("*.json"),reverse=True)[:max(1,min(limit,500))]:
        try: items.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception: continue
    return {"ok":True,"system":"BRAIN_DIWAN","cases":items}

@app.get("/v1/diwan/cases/{case_id}",dependencies=[Depends(require_auth)])
def diwan_get_case(case_id:str):
    item=_diwan_load(DIWAN_CASES,case_id)
    if not item: raise HTTPException(404,"case not found")
    return {"ok":True,"system":"BRAIN_DIWAN","case":item}

@app.post("/v1/diwan/correspondence/{correspondence_id}/route",dependencies=[Depends(require_auth)])
def diwan_route(correspondence_id:str,body:DiwanRouteRequest):
    item=_diwan_load(DIWAN_CORRESPONDENCE,correspondence_id)
    if not item: raise HTTPException(404,"correspondence not found")
    record=item["record"]; c=Correspondence(**{**record,"state":CorrespondenceState(record["state"])})
    try:
        if c.state==CorrespondenceState.REGISTERED: c.transition(CorrespondenceState.CLASSIFIED,body.assigned_by,"classification")
        if c.state==CorrespondenceState.CLASSIFIED: c.transition(CorrespondenceState.LINKED,body.assigned_by,"routing")
        if c.state==CorrespondenceState.LINKED: c.transition(CorrespondenceState.ROUTED,body.assigned_by,"routing")
    except ValueError as exc: raise HTTPException(409,str(exc))
    item["record"]={k:(v.value if hasattr(v,"value") else v) for k,v in c.__dict__.items()}
    item["routing"]=RoutingAssignment(correspondence_id,body.target,body.assigned_by,deadline_at=body.deadline_at,notes=body.notes).__dict__
    _diwan_store(DIWAN_CORRESPONDENCE,correspondence_id,item)
    return {"ok":True,"system":"BRAIN_DIWAN","correspondence":item["record"],"routing":item["routing"]}

@app.get("/v1/diwan/records/archive-check",dependencies=[Depends(require_auth)])
def diwan_archive_check(state:str,legal_hold:bool=False):
    try: eligible=archive_eligible(RecordState(state),legal_hold)
    except ValueError: raise HTTPException(400,"invalid record state")
    return {"ok":True,"system":"BRAIN_DIWAN","archive_eligible":eligible,"legal_hold":legal_hold}



class FeedbackCreateRequest(BaseModel):
    customer_id: str|None=None
    rating: int|None=None
    category: str
    body: str
    consent_to_contact: bool=False
    marketing_consent: bool=False
    request_id: str|None=None
    case_id: str|None=None

class FeedbackTransitionRequest(BaseModel):
    state: str
    actor: str
    evidence_ref: str|None=None
    reason: str=""


@app.post("/v1/feedback")
def create_feedback(body: FeedbackCreateRequest):
    try:
        f=FEEDBACK_STORE.create(**body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc))
    return {"ok":True,"feedback":asdict(f)}

@app.get("/v1/feedback",dependencies=[Depends(require_auth)])
def list_feedback(limit:int=100):
    return {"ok":True,"feedback":[asdict(f) for f in FEEDBACK_STORE.list(limit)]}

@app.get("/v1/feedback/{feedback_id}",dependencies=[Depends(require_auth)])
def get_feedback(feedback_id:str):
    try: f=FEEDBACK_STORE.get(feedback_id)
    except FileNotFoundError: raise HTTPException(status_code=404,detail="feedback not found")
    return {"ok":True,"feedback":asdict(f)}

@app.post("/v1/feedback/{feedback_id}/transition",dependencies=[Depends(require_auth)])
def transition_feedback(
    feedback_id: str,
    body: FeedbackTransitionRequest | None = None,
    state: str | None = None,
    evidence_ref: str | None = None,
    actor: str | None = None,
    reason: str = "",
):
    """Transition feedback state with JSON-body and legacy query-parameter compatibility."""
    request_body = body
    requested_state = (request_body.state if request_body else state)
    requested_evidence = (request_body.evidence_ref if request_body else evidence_ref)
    requested_actor = (request_body.actor if request_body else actor) or "api-client"
    requested_reason = (request_body.reason if request_body else reason)
    if not requested_state:
        raise HTTPException(status_code=422, detail="state is required")
    try:
        f = FEEDBACK_STORE.get(feedback_id)
        target = FeedbackState(requested_state.upper())
        f.transition(target, requested_actor, requested_evidence, requested_reason)
        FEEDBACK_STORE.save(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="feedback not found")
    except ValueError as exc:
        detail = str(exc)
        status_code = 422 if detail.startswith("invalid transition") or "requires evidence_ref" in detail else 409
        raise HTTPException(status_code=status_code, detail=detail)
    return {"ok": True, "feedback": asdict(f)}

class CommunicationCreateRequest(BaseModel):
    customer_id: str
    channel: str
    direction: str
    body: str
    thread_id: str | None = None
    case_id: str | None = None
    request_id: str | None = None
    consent_scope: str | None = None
    idempotency_key: str | None = None


@app.post("/v1/communications", dependencies=[Depends(require_auth)])
def create_communication(body: CommunicationCreateRequest):
    try:
        channel = Channel(body.channel.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="unsupported communication channel")
    try:
        msg = COMMUNICATION_HUB.create(
            customer_id=body.customer_id,
            channel=channel,
            direction=body.direction.upper(),
            body=body.body,
            thread_id=body.thread_id,
            case_id=body.case_id,
            request_id=body.request_id,
            consent_scope=body.consent_scope,
            idempotency_key=body.idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "message": asdict(msg) if "asdict" in globals() else msg.__dict__}


@app.get("/v1/communications/customer/{customer_id}", dependencies=[Depends(require_auth)])
def list_customer_communications(customer_id: str, limit: int = 100):
    items = COMMUNICATION_HUB.list_customer(customer_id)
    return {"ok": True, "customer_id": customer_id, "messages": [m.__dict__ for m in items[-max(1, min(limit, 500)):]]}


@app.get("/v1/communications/{message_id}", dependencies=[Depends(require_auth)])
def get_communication(message_id: str):
    try:
        msg = COMMUNICATION_HUB.get(message_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="communication not found")
    return {"ok": True, "message": msg.__dict__}


class CommunicationTransitionRequest(BaseModel):
    state: str
    evidence_ref: str | None = None


@app.post("/v1/communications/{message_id}/transition", dependencies=[Depends(require_auth)])
def transition_communication(message_id: str, body: CommunicationTransitionRequest):
    try:
        state = MessageState(body.state.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="unsupported communication state")
    try:
        msg = COMMUNICATION_HUB.transition(message_id, state, body.evidence_ref)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="communication not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"ok": True, "message": msg.__dict__}

"""Brain Dيوان: durable human-approval inbox and notification outbox.

The approval record is the system of record. Email is a notification channel,
not the authoritative place where a decision is stored.
"""
from __future__ import annotations
import hashlib, hmac, json, os, smtplib, time, uuid
from email.message import EmailMessage
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.getenv("BRAIN_STATE_DIR", str(ROOT / ".brain_state")))
APPROVAL_DIR = STATE / "approvals"
OUTBOX_DIR = STATE / "notification_outbox"

def _safe_id(value: str) -> str:
    if not value or "/" in value or "\\" in value or value in {".", ".."}:
        raise ValueError("invalid identifier")
    return value

def _path(directory: Path, identifier: str) -> Path:
    return directory / (_safe_id(identifier) + ".json")

def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def create_approval(*, subject: str, reason: str, risk: str = "MEDIUM",
                    requested_action: str = "APPROVE",
                    evidence: list[dict[str, Any]] | None = None,
                    recipient_email: str | None = None,
                    source_type: str = "BRAIN", source_id: str | None = None,
                    metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    approval_id = str(uuid.uuid4())
    now = time.time()
    approval = {
        "approval_id": approval_id, "status": "PENDING",
        "subject": subject.strip(), "reason": reason.strip(),
        "risk": risk.upper(), "requested_action": requested_action,
        "evidence": evidence or [], "recipient_email": recipient_email,
        "source": {"type": source_type, "id": source_id},
        "metadata": metadata or {}, "created_at": now, "updated_at": now,
        "decision": None, "events": [{"event": "APPROVAL_CREATED", "at": now}],
    }
    _write(_path(APPROVAL_DIR, approval_id), approval)
    if recipient_email:
        enqueue_email(approval)
    return approval

def get_approval(approval_id: str) -> dict[str, Any] | None:
    path = _path(APPROVAL_DIR, approval_id)
    return _read(path) if path.exists() else None

def list_approvals(status: str | None = "PENDING", limit: int = 100) -> list[dict[str, Any]]:
    APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in APPROVAL_DIR.glob("*.json"):
        try: item = _read(path)
        except (OSError, json.JSONDecodeError): continue
        if status and item.get("status") != status: continue
        items.append(item)
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:max(1, min(int(limit), 500))]

def decide_approval(approval_id: str, *, decision: str, actor: str, note: str = "") -> dict[str, Any]:
    approval = get_approval(approval_id)
    if not approval: raise KeyError("approval not found")
    if approval["status"] != "PENDING": raise ValueError("approval is no longer pending")
    normalized = decision.upper().strip()
    if normalized not in {"APPROVED", "REJECTED", "RETURNED"}:
        raise ValueError("unsupported decision")
    now = time.time()
    approval["status"] = normalized
    approval["updated_at"] = now
    approval["decision"] = {"decision": normalized, "actor": actor, "note": note.strip(), "at": now}
    approval.setdefault("events", []).append({
        "event": "HUMAN_DECISION_RECORDED", "decision": normalized, "actor": actor, "at": now
    })
    _write(_path(APPROVAL_DIR, approval_id), approval)
    return approval

def _approval_url(approval_id: str) -> str:
    base = os.getenv("BRAIN_PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/#/approvals/{approval_id}" if base else f"/#/approvals/{approval_id}"

def _signed_action_token(approval_id: str) -> str:
    secret = os.getenv("BRAIN_APPROVAL_LINK_SECRET", "")
    if not secret: return ""
    return hmac.new(secret.encode(), approval_id.encode(), hashlib.sha256).hexdigest()

def enqueue_email(approval: dict[str, Any]) -> dict[str, Any]:
    approval_id = approval["approval_id"]
    token = _signed_action_token(approval_id)
    item = {
        "notification_id": str(uuid.uuid4()), "type": "APPROVAL_REQUEST",
        "status": "QUEUED", "approval_id": approval_id,
        "to": approval.get("recipient_email"),
        "subject": f"[BRAIN] موافقة مطلوبة: {approval['subject']}",
        "body": (
            f"يوجد طلب موافقة داخل ديوان Brain.\\n\\n"
            f"الطلب: {approval['subject']}\\nالسبب: {approval['reason']}\\n"
            f"المخاطر: {approval['risk']}\\n\\n"
            f"افتح الديوان: {_approval_url(approval_id)}\\n"
            f"رمز الإشعار: {token or 'USE_AUTHENTICATED_DASHBOARD'}"
        ),
        "created_at": time.time(),
    }
    _write(_path(OUTBOX_DIR, item["notification_id"]), item)
    if os.getenv("BRAIN_SMTP_HOST"):
        try:
            _send_smtp(item); item["status"] = "SENT"; item["sent_at"] = time.time()
            _write(_path(OUTBOX_DIR, item["notification_id"]), item)
        except Exception as exc:
            item["status"] = "FAILED"; item["error"] = str(exc)
            _write(_path(OUTBOX_DIR, item["notification_id"]), item)
    return item

def _send_smtp(item: dict[str, Any]) -> None:
    host = os.environ["BRAIN_SMTP_HOST"]
    port = int(os.getenv("BRAIN_SMTP_PORT", "587"))
    username = os.getenv("BRAIN_SMTP_USERNAME", "")
    password = os.getenv("BRAIN_SMTP_PASSWORD", "")
    sender = os.getenv("BRAIN_SMTP_FROM", username)
    if not item.get("to") or not sender: raise RuntimeError("SMTP recipient/from is not configured")
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = item["subject"], sender, item["to"]
    msg.set_content(item["body"])
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        if username: server.login(username, password)
        server.send_message(msg)

def notification_status(limit: int = 100) -> list[dict[str, Any]]:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in OUTBOX_DIR.glob("*.json"):
        try: items.append(_read(path))
        except (OSError, json.JSONDecodeError): continue
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:max(1, min(int(limit), 500))]

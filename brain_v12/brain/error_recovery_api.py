"""Unified, evidence-first error intake for Electronic Brain nodes.

Reports are normalized and persisted locally. Optional simulator forwarding is
best-effort and sends only the redacted report. Proposed repairs are never run
by this API; execution remains behind Brain's existing permission/verification
gates.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request

from .control_auth import require_control_key

router = APIRouter(tags=["brain-error-recovery"])
_LOCK = threading.Lock()
_SECRET_PATTERNS = [
    re.compile(r"(?i)(token|password|secret|api[_-]?key|authorization)\\s*[:=]\\s*([^\\s,;]+)"),
    re.compile(r"(?i)bearer\\s+[A-Za-z0-9._~+/-]+=*"),
]


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): ("[REDACTED]" if re.search(r"(?i)(token|password|secret|api[_-]?key|authorization)", str(k)) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value[:100]]
    if isinstance(value, str):
        text = value[:8000]
        for pattern in _SECRET_PATTERNS:
            text = pattern.sub(lambda m: (m.group(1) + "=[REDACTED]") if m.lastindex and m.lastindex >= 2 else "Bearer [REDACTED]", text)
        return text
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:1000]


def _store_path() -> Path:
    return Path(os.getenv("BRAIN_ERROR_STORE", ".brain/state/error-recovery.jsonl"))


def _load_recent(path: Path, limit: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def _fingerprint(source: str, message: str, context: dict[str, Any]) -> str:
    stable = {"source": source, "message": message.strip().lower(), "component": context.get("component"), "code": context.get("code")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()[:24]


def _severity(message: str, requested: str) -> str:
    if requested in {"critical", "high", "medium", "low"}:
        return requested
    text = message.lower()
    if any(x in text for x in ("data loss", "security breach", "credential leak", "corruption")):
        return "critical"
    if any(x in text for x in ("failed", "exception", "unauthorized", "timeout", "crash")):
        return "high"
    return "medium"


def _forward(report: dict[str, Any]) -> dict[str, Any]:
    url = os.getenv("BRAIN_CHAT_SIMULATOR_URL", "").strip()
    if not url:
        return {"status": "NOT_CONFIGURED", "forwarded": False}
    try:
        response = httpx.post(url, json={"type": "brain_error_report", "report": report,
            "instruction": "Diagnose root cause; propose a safe fix, required scripts/tools, tests and rollback. Do not claim execution. Do not request or expose secrets."}, timeout=8.0)
        return {"status": "FORWARDED" if response.is_success else "FORWARD_FAILED",
                "forwarded": response.is_success, "http_status": response.status_code}
    except httpx.HTTPError:
        return {"status": "FORWARD_FAILED", "forwarded": False}


@router.post("/api/errors/report")
def report_error(request: Request, body: dict):
    """Receive an error from Termux, Desktop Commander, Azure, GitHub, or Brain."""
    require_control_key(request)
    source = str(body.get("source", "")).strip().lower()
    allowed = {"termux-brain", "desktop-commander-brain", "azure-brain", "github-brain", "brain-runtime"}
    if source not in allowed:
        raise HTTPException(status_code=422, detail={"error": "INVALID_ERROR_SOURCE", "allowed": sorted(allowed)})
    message = str(body.get("message", body.get("error", ""))).strip()
    if not message:
        raise HTTPException(status_code=422, detail="ERROR_MESSAGE_REQUIRED")
    if len(message) > 8000:
        raise HTTPException(status_code=413, detail="ERROR_MESSAGE_TOO_LARGE")
    context = _redact(body.get("context", {}))
    if not isinstance(context, dict):
        context = {"detail": context}
    safe_message = _redact(message)
    fingerprint = _fingerprint(source, safe_message, context)
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        recent = _load_recent(path)
        duplicate = next((item for item in reversed(recent) if item.get("fingerprint") == fingerprint and item.get("status") != "RESOLVED"), None)
        if duplicate:
            return {"ok": True, "status": "DUPLICATE", "incident_id": duplicate["incident_id"], "fingerprint": fingerprint}
        report = {
            "incident_id": "ERR-" + uuid4().hex[:12],
            "fingerprint": fingerprint,
            "source": source,
            "severity": _severity(safe_message, str(body.get("severity", "")).lower()),
            "message": safe_message,
            "context": context,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "RECEIVED",
            "repair_policy": "PROPOSE_AND_VERIFY; NO_UNGUARDED_EXECUTION",
        }
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False) + "\\n")
    forwarding = _forward(report)
    return {"ok": True, "status": "RECEIVED", "incident_id": report["incident_id"],
            "fingerprint": fingerprint, "severity": report["severity"], "simulator": forwarding}


@router.get("/api/errors/recent")
def recent_errors(request: Request, limit: int = 50):
    require_control_key(request)
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="LIMIT_MUST_BE_1_TO_200")
    reports = _load_recent(_store_path(), limit=limit)
    return {"ok": True, "count": len(reports), "reports": reports}

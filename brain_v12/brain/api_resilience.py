"""API Reliability Control Plane.

One canonical diagnostic path for recurring Brain API/runtime failures.
This layer does not replace existing endpoints; it routes diagnosis to the
correct existing path and prevents ad-hoc endpoint guessing.
"""
from __future__ import annotations

import time
from fastapi import APIRouter, Request

from .control_auth import require_control_key

STAGES = (
    ("runtime", "/api/system/readiness"),
    ("media", "/api/media/health"),
    ("agent_status", "/api/agent-gateway/status"),
    ("agent_diagnostics", "/api/agent-gateway/diagnostics"),
    ("queue", "/api/device/queue"),
    ("device_status", "/api/device/status"),
    ("heartbeat", "/api/device/heartbeat"),
    ("poll", "/api/device/poll"),
    ("report", "/api/device/report"),
    ("result", "/api/agent-gateway/result/{task_id}"),
    ("verify", "/api/agent-gateway/verify/{task_id}"),
)

def router_factory(device_bridge, liveness_reader):
    router = APIRouter(prefix="/api/resilience", tags=["api-resilience"])

    @router.get("/paths")
    def paths():
        return {
            "ok": True,
            "mode": "CANONICAL_API_PATHS",
            "order": [name for name, _ in STAGES],
            "paths": {name: path for name, path in STAGES},
            "rule": "diagnose_stage_first; repair_only_the_failed_stage; verify_before_next_stage",
        }

    @router.get("/status")
    def status():
        checks = {}
        try:
            checks["runtime"] = liveness_reader()
        except Exception as exc:
            checks["runtime"] = {"ok": False, "error": str(exc)[:300]}
        try:
            checks["device"] = device_bridge.agent_status()
        except Exception as exc:
            checks["device"] = {"ok": False, "error": str(exc)[:300]}
        return {
            "ok": True,
            "controller": "API_RELIABILITY_CONTROL_PLANE",
            "ts": time.time(),
            "checks": checks,
            "next": _next_path(checks),
        }

    @router.post("/diagnose")
    def diagnose(request: Request):
        require_control_key(request)
        checks = {}
        errors = {}
        try:
            checks["runtime"] = liveness_reader()
        except Exception as exc:
            errors["runtime"] = str(exc)[:500]
        try:
            checks["device"] = device_bridge.agent_status()
        except Exception as exc:
            errors["device"] = str(exc)[:500]

        return {
            "ok": not errors,
            "controller": "API_RELIABILITY_CONTROL_PLANE",
            "failed": list(errors),
            "next": _next_path(checks, errors),
            "checks": checks,
            "errors": errors,
            "recovery_order": [
                "runtime",
                "auth",
                "agent_status",
                "queue",
                "heartbeat",
                "poll",
                "report",
                "result",
                "verify",
            ],
            "rule": "never_restart_or_rebuild_APK_before_stage_failure_is_evidenced",
        }

    return router

def _next_path(checks, errors=None):
    errors = errors or {}
    if "runtime" in errors or not _looks_ok(checks.get("runtime")):
        return {"stage": "runtime", "path": "/api/system/readiness"}
    if "device" in errors:
        return {"stage": "agent_status", "path": "/api/agent-gateway/status"}
    device = checks.get("device") or {}
    if isinstance(device, dict):
        failed = int(device.get("failed", 0) or 0)
        queued = int(device.get("queued", 0) or 0)
        if failed > 0:
            return {"stage": "result", "path": "/api/agent-gateway/result/{task_id}", "reason": "failed_tasks_present"}
        if queued > 0:
            return {"stage": "poll", "path": "/api/device/poll", "reason": "queue_pending"}
    return {"stage": "verify", "path": "/api/agent-gateway/verify/{task_id}", "reason": "runtime_and_agent_healthy"}

def _looks_ok(value):
    if value is None:
        return False
    if isinstance(value, dict):
        if value.get("ok") is False:
            return False
        if str(value.get("status", "")).upper() in {"DOWN", "ERROR", "NOT_READY", "UNAVAILABLE"}:
            return False
    return True

"""Brain liveness and readiness assessment.

This module deliberately separates the Brain process being alive from optional
workers/devices being connected. A missing Android/Termux agent must not make
the Brain itself look dead.
"""

import time


def assess(*, store, device_bridge, cognitive) -> dict:
    checked_at = time.time()
    checks = {}

    try:
        state = store.state()
        checks["database"] = {"ok": True, "status": "RESPONDING"}
    except Exception as exc:
        state = {}
        checks["database"] = {"ok": False, "status": "ERROR", "error": str(exc)[:300]}

    runtime_error = isinstance(state, dict) and state.get("status") == "ERROR"
    checks["runtime"] = {
        "ok": not runtime_error,
        "status": "ERROR" if runtime_error else "RESPONDING",
        "stage": state.get("cognitive_stage", "READY") if isinstance(state, dict) else "UNKNOWN",
    }

    try:
        device = device_bridge.status()
        checks["device_bridge"] = {
            "ok": bool(device.get("configured")),
            "configured": bool(device.get("configured")),
            "queued": int(device.get("queued", 0) or 0),
            "pending": int(device.get("pending", 0) or 0),
            "completed": int(device.get("completed", 0) or 0),
            "failed": int(device.get("failed", 0) or 0),
            "agents_online": bool(device.get("agents", {}).get("online")),
            "agents": device.get("agents", {}),
        }
    except Exception as exc:
        device = {}
        checks["device_bridge"] = {"ok": False, "status": "ERROR", "error": str(exc)[:300]}

    try:
        stage = getattr(cognitive, "STAGES", [])
        checks["cognitive"] = {
            "ok": True,
            "status": "READY",
            "stage_count": len(stage),
        }
    except Exception as exc:
        checks["cognitive"] = {"ok": False, "status": "ERROR", "error": str(exc)[:300]}

    core_ok = all(checks[name]["ok"] for name in ("database", "runtime", "cognitive"))
    worker_ok = checks["device_bridge"]["ok"]
    overall = "ALIVE" if core_ok and worker_ok else "DEGRADED" if core_ok else "ERROR"

    return {
        "ok": core_ok,
        "status": overall,
        "brain_alive": core_ok,
        "checked_at": checked_at,
        "checks": checks,
        "definition": {
            "ALIVE": "Brain process, database, runtime state and cognitive layer respond.",
            "DEGRADED": "Brain core is alive but an optional execution dependency is unavailable.",
            "ERROR": "A core Brain dependency failed.",
        },
    }

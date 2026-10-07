"""Brain liveness and readiness assessment.

This module deliberately separates the Brain process being alive from optional
workers/devices being connected. A missing Android/Termux agent must not make
the Brain itself look dead.
"""

import time



def run_execution_probe(device_bridge, timeout=8):
    """Queue a harmless python_version probe and wait briefly for its result."""
    try:
        created = device_bridge.enqueue("python_version", {})
        if not created.get("ok"):
            return {"ok": False, "status": "PROBE_ENQUEUE_FAILED", "error": created.get("error", "unknown")}
        task_id = created["task"]["task_id"]
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = device_bridge.result(task_id)
            if result.get("status") == "COMPLETED":
                verified = device_bridge.verify_result(task_id)
                return {"ok": bool(verified.get("verified", True)), "status": "PROBE_COMPLETED", "task_id": task_id, "agent_id": result.get("agent_id"), "verification": verified}
            if result.get("status") == "FAILED":
                return {"ok": False, "status": "PROBE_FAILED", "task_id": task_id, "error": result.get("error", "")}
            time.sleep(0.25)
        return {"ok": False, "status": "PROBE_TIMEOUT", "task_id": task_id}
    except Exception as exc:
        return {"ok": False, "status": "PROBE_ERROR", "error": str(exc)[:300]}

def assess(*, store, device_bridge, cognitive, probe_result=None) -> dict:
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

    if probe_result is not None:
        checks["execution_probe"] = dict(probe_result)
    core_ok = all(checks[name]["ok"] for name in ("database", "runtime", "cognitive"))
    worker_ok = checks["device_bridge"]["ok"]
    probe_ok = checks.get("execution_probe", {}).get("ok", True)
    overall = "ALIVE" if core_ok and worker_ok and probe_ok else "DEGRADED" if core_ok else "ERROR"

    return {
        "ok": core_ok,
        "status": overall,
        "brain_alive": core_ok,
        "execution_alive": probe_ok,
        "checked_at": checked_at,
        "checks": checks,
        "definition": {
            "ALIVE": "Brain process, database, runtime state and cognitive layer respond.",
            "DEGRADED": "Brain core is alive but an optional execution dependency is unavailable.",
            "ERROR": "A core Brain dependency failed.",
        },
    }

def assess_full(*, store, device_bridge, cognitive, probe_timeout=8):
    """Run the evidence-based Brain life certificate, including a safe execution probe."""
    probe = run_execution_probe(device_bridge, timeout=probe_timeout)
    result = assess(store=store, device_bridge=device_bridge, cognitive=cognitive, probe_result=probe)
    checks = result["checks"]
    agent_online = bool(checks.get("device_bridge", {}).get("agents_online"))
    if not result["brain_alive"]:
        truth = "RUNTIME_DEAD"
    elif not checks.get("device_bridge", {}).get("ok"):
        truth = "EXECUTOR_OFFLINE"
    elif not agent_online:
        truth = "AGENT_OFFLINE"
    elif not probe.get("ok"):
        truth = "EXECUTION_FAILED"
    else:
        truth = "FULLY_ALIVE"
    result["life_certificate"] = {
        "status": truth,
        "verified": truth == "FULLY_ALIVE",
        "checks": ["process","database","runtime","cognitive","device_bridge","agent","safe_execution_probe","result_verification"],
    }
    return result


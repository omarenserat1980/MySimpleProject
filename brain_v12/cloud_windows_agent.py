from __future__ import annotations

"""Windows Cloud node registration/heartbeat helper.

Runs inside a real Windows Server 2025 cloud VM. It never provisions
infrastructure and never stores provider credentials. The VM must be
enrolled with Brain Cloud Fabric and then reports its capability/heartbeat.
"""

import os
import platform
import time
import urllib.request
import json
import subprocess


def _post(url: str, payload: dict, token: str) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode())


def heartbeat() -> dict:
    origin = os.getenv("BRAIN_FABRIC_URL", "").rstrip("/")
    node_id = os.getenv("BRAIN_WINDOWS_NODE_ID", platform.node()).strip()
    token = os.getenv("BRAIN_ENROLLMENT_TOKEN", "").strip()
    if not origin or not node_id or not token:
        return {
            "ok": False,
            "status": "NOT_CONFIGURED",
            "reason": "BRAIN_FABRIC_URL_NODE_ID_OR_ENROLLMENT_TOKEN_MISSING",
        }

    payload = {
        "enrollment_token": token,
        "state": "READY",
        "jobs_running": 0,
        "architecture": "x86_64" if platform.machine().lower() in {"amd64", "x86_64"} else platform.machine(),
        "capabilities": [
            "windows-server-2025",
            "windows-cloud",
            "brain-task-execution",
            "brain-heartbeat",
            "brain-evidence",
        ],
    }
    result = _post(f"{origin}/v1/fabric/nodes/{node_id}/heartbeat", payload, token)
    return {"ok": True, "status": "HEARTBEAT_SENT", "node": result.get("node")}


def _get(url: str, token: str) -> dict:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode())


def _post_result(origin: str, node_id: str, job_id: str, token: str, state: str, evidence: dict) -> dict:
    return _post(
        f"{origin}/v1/fabric/nodes/{node_id}/jobs/{job_id}/result",
        {"state": state, "evidence": evidence},
        token,
    )


def execute_job(job: dict) -> dict:
    if os.name != "nt":
        raise RuntimeError("WINDOWS_AGENT_REQUIRES_WINDOWS")
    payload = job.get("payload") or {}
    argv = payload.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise RuntimeError("WINDOWS_JOB_REQUIRES_ARGV_LIST")
    timeout = max(1, min(int(payload.get("timeout_seconds", 900)), 3600))
    cwd = payload.get("cwd")
    if cwd is not None and not isinstance(cwd, str):
        raise RuntimeError("WINDOWS_JOB_CWD_INVALID")
    started = time.time()
    completed = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        check=False,
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-20000:],
        "stderr": completed.stderr[-20000:],
        "duration_seconds": round(time.time() - started, 3),
        "shell": False,
        "executor": "windows-server-2025-cloud-agent",
    }


def poll_once() -> dict:
    origin = os.getenv("BRAIN_FABRIC_URL", "").rstrip("/")
    node_id = os.getenv("BRAIN_WINDOWS_NODE_ID", platform.node()).strip()
    token = os.getenv("BRAIN_ENROLLMENT_TOKEN", "").strip()
    if not origin or not node_id or not token:
        return {"ok": False, "status": "NOT_CONFIGURED"}
    job_response = _get(
        f"{origin}/v1/fabric/nodes/{node_id}/jobs/next",
        token,
    )
    job = job_response.get("job")
    if not job:
        return {"ok": True, "status": "IDLE"}
    try:
        evidence = execute_job(job)
        state = "SUCCESS" if evidence["exit_code"] == 0 else "FAILED"
    except subprocess.TimeoutExpired as exc:
        evidence = {
            "error": "PROCESS_TIMEOUT",
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-20000:] if isinstance(exc.stderr, str) else "",
            "executor": "windows-server-2025-cloud-agent",
        }
        state = "FAILED"
    except Exception as exc:
        evidence = {
            "error": f"{type(exc).__name__}:{exc}",
            "executor": "windows-server-2025-cloud-agent",
        }
        state = "FAILED"
    result = _post_result(origin, node_id, job["job_id"], token, state, evidence)
    return {"ok": True, "status": "JOB_COMPLETED", "job_id": job["job_id"], "state": state, "result": result}


def run_forever(poll_seconds: float = 5.0) -> None:
    interval = max(1.0, float(poll_seconds))
    while True:
        heartbeat()
        poll_once()
        time.sleep(interval)


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("Windows Cloud Agent must run on Windows")
    result = heartbeat()
    if result.get("ok"):
        run_forever(float(os.getenv("BRAIN_WINDOWS_AGENT_POLL_SECONDS", "5")))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result.get("ok") else 2)

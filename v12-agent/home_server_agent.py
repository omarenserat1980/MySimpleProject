#!/usr/bin/env python3
"""Outbound-only worker for Brain Home Server's durable task queue.

Configure BRAIN_HOME_SERVER_URL (or V12_BRAIN_URL) to the HTTPS origin that
serves /api/home-server routes. The key file must contain the same secret as
the server's BRAIN_AGENT_KEY (or another explicitly supported worker-key env).
Only fixed, allowlisted diagnostics are executed; arbitrary shell commands are
never accepted.
"""
from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = (
    os.getenv("BRAIN_HOME_SERVER_URL", "").strip()
    or os.getenv("V12_BRAIN_URL", "").strip()
).rstrip("/")
AGENT_ID = os.getenv("BRAIN_HOME_SERVER_WORKER_ID", os.getenv("V12_AGENT_ID", "redmi3-01")).strip()
KEY_FILE = Path(os.getenv("BRAIN_HOME_SERVER_KEY_FILE", os.getenv(
    "V12_AGENT_KEY_FILE", str(Path.home() / "v12-agent" / "agent.key")
))).expanduser()
POLL_SECONDS = max(2.0, min(60.0, float(os.getenv("BRAIN_HOME_SERVER_POLL_SECONDS", "3"))))
LEASE_SECONDS = max(10, min(900, int(os.getenv("BRAIN_HOME_SERVER_LEASE_SECONDS", "60"))))
CAPABILITIES = ["python", "platform", "status", "self_test"]


def load_key() -> str:
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("HOME_SERVER_WORKER_KEY_EMPTY")
    return key


def request_json(method: str, path: str, key: str, payload: dict | None = None) -> dict:
    if not BASE_URL.startswith("https://") and not BASE_URL.startswith("http://127.0.0.1"):
        raise RuntimeError("SET_BRAIN_HOME_SERVER_URL_TO_HTTPS_OR_LOCALHOST")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer " + key,
        "User-Agent": "Brain-Home-Server-Worker/1.0",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = Request(BASE_URL + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=25) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("HOME_SERVER_RESPONSE_NOT_OBJECT")
    return decoded


def execute_task(task_name: str, params: dict | None = None) -> dict:
    """Execute only fixed diagnostics; never evaluate user-supplied commands."""
    if task_name == "status":
        return {
            "agent": "Brain-Home-Server-Worker",
            "agent_id": AGENT_ID,
            "status": "READY",
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
    if task_name == "python_version":
        return {"python": platform.python_version(), "executable": os.sys.executable}
    if task_name == "platform":
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }
    if task_name == "brain_self_test":
        return {
            "ok": True,
            "python_available": bool(platform.python_version()),
            "working_directory_exists": Path.cwd().is_dir(),
            "agent_id": AGENT_ID,
        }
    raise ValueError("TASK_NOT_ALLOWED")


def run_once(key: str) -> dict:
    claimed = request_json("POST", "/api/home-server/claim", key, {
        "worker_id": AGENT_ID,
        "lease_seconds": LEASE_SECONDS,
        "capabilities": CAPABILITIES,
    })
    task = claimed.get("task")
    if not task:
        return {"ok": True, "status": claimed.get("status", "IDLE"), "task": None}
    task_id = str(task.get("task_id", ""))
    task_name = str(task.get("task", ""))
    if not task_id:
        raise ValueError("CLAIMED_TASK_ID_MISSING")
    try:
        result = execute_task(task_name, task.get("params") or {})
        report = {"worker_id": AGENT_ID, "ok": True, "result": result, "error": ""}
    except Exception as exc:
        report = {"worker_id": AGENT_ID, "ok": False, "result": {}, "error": str(exc)[:4000]}
    returned = request_json(
        "POST", "/api/home-server/tasks/" + task_id + "/report", key, report
    )
    return {
        "ok": bool(returned.get("ok")),
        "task_id": task_id,
        "task": task_name,
        "reported_status": (returned.get("task") or {}).get("status"),
    }


def main() -> None:
    if not BASE_URL:
        raise SystemExit("Configure BRAIN_HOME_SERVER_URL before starting this worker.")
    if not AGENT_ID:
        raise SystemExit("BRAIN_HOME_SERVER_WORKER_ID must not be empty.")
    key = load_key()
    print("Brain Home Server Worker online")
    print("Base URL:", BASE_URL)
    print("Worker ID:", AGENT_ID)
    print("Allowed tasks:", ", ".join(sorted({"status", "python_version", "platform", "brain_self_test"})))
    while True:
        try:
            result = run_once(key)
            if result.get("task_id"):
                print(json.dumps(result, ensure_ascii=False))
        except KeyboardInterrupt:
            print("Brain Home Server Worker stopped")
            return
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
            # Never print credentials or request headers.
            print("WORKER_WARNING:", str(exc)[:300])
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

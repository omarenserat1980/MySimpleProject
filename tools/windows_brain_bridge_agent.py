#!/usr/bin/env python3
"""Opt-in, outbound-only Windows bridge for Electronic Brain.

Only fixed, read-only tasks are supported. This agent never opens a listener,
runs shell commands, installs software, or provisions resources.
"""
from __future__ import annotations

import json
import math
import os
import platform
import shutil
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

AGENT_ID = os.getenv("V12_AGENT_ID", "windows-bridge-01").strip()
BRAIN_URL = os.getenv("V12_BRAIN_URL", "").strip().rstrip("/")
KEY_FILE = Path(os.getenv("V12_AGENT_KEY_FILE", str(Path.home() / ".brain" / "agent.key")))
POLL_SECONDS = 10.0
ALLOWED_TASKS = frozenset({"status", "platform", "python_version"})


class _NoRedirectHandler(HTTPRedirectHandler):
    """Reject redirects so agent credentials stay bound to the configured endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_config() -> None:
    global AGENT_ID, BRAIN_URL, KEY_FILE, POLL_SECONDS
    # Read the environment at call time so tests and startup validation use the
    # active process configuration rather than import-time defaults.
    agent_id = os.getenv("V12_AGENT_ID", AGENT_ID).strip()
    brain_url = os.getenv("V12_BRAIN_URL", BRAIN_URL).strip().rstrip("/")
    if not agent_id.startswith("windows-bridge-"):
        raise RuntimeError("V12_AGENT_ID_MUST_START_WITH_windows-bridge-")
    if not brain_url:
        raise RuntimeError("V12_BRAIN_URL_REQUIRED")
    if any(c in brain_url for c in "\r\n"):
        raise RuntimeError("INVALID_BRAIN_URL")
    parsed = urlsplit(brain_url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http"
        and os.getenv("BRAIN_ALLOW_INSECURE_HTTP", "").strip() == "1"
    ):
        raise RuntimeError("HTTPS_REQUIRED_SET_BRAIN_ALLOW_INSECURE_HTTP=1_ONLY_FOR_TRUSTED_TEST_NETWORK")
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        # API paths are appended by this client; accepting a base path here
        # would silently produce duplicated paths such as /api/api/device/heartbeat.
        raise RuntimeError("INVALID_BRAIN_URL")
    allowed_hosts = {
        item.strip().lower()
        for item in os.getenv("V12_BRAIN_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    }
    if not allowed_hosts:
        raise RuntimeError("V12_BRAIN_ALLOWED_HOSTS_REQUIRED")
    if parsed.hostname.lower() not in allowed_hosts:
        raise RuntimeError("BRAIN_HOST_NOT_ALLOWLISTED")

    try:
        poll_seconds = float(os.getenv("V12_POLL_SECONDS", "10"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("INVALID_V12_POLL_SECONDS") from exc
    if not math.isfinite(poll_seconds):
        raise RuntimeError("INVALID_V12_POLL_SECONDS")

    # Apply configuration only after every field has passed validation.
    # This prevents a partially updated runtime if one setting is malformed.
    AGENT_ID = agent_id
    BRAIN_URL = brain_url.rstrip("/")
    KEY_FILE = Path(os.getenv("V12_AGENT_KEY_FILE", str(Path.home() / ".brain" / "agent.key")))
    POLL_SECONDS = max(5.0, min(60.0, poll_seconds))

def load_key() -> str:
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise RuntimeError("AGENT_KEY_EMPTY")
    return key


def request_json(method: str, path: str, key: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    headers = {
        "Accept": "application/json",
        "X-V12-Agent-Key": key,
        "X-V12-Agent-Id": AGENT_ID,
        "User-Agent": "ElectronicBrain-WindowsBridge/1.0",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(BRAIN_URL + path, data=data, headers=headers, method=method)
    # urllib's default redirect handler can follow a server-supplied Location.
    # Disable redirects so X-V12-Agent-Key is never sent to a redirected host.
    with build_opener(_NoRedirectHandler()).open(request, timeout=8) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise RuntimeError("BRAIN_RESPONSE_TOO_LARGE")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("BRAIN_RESPONSE_INVALID")
    return value


def resource_snapshot() -> dict:
    """Return bounded host telemetry; never imply resources are reserved for Brain."""
    usage = shutil.disk_usage(Path.home())
    memory = {"available_bytes": None, "total_bytes": None}
    if os.name == "nt":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                memory = {
                    "available_bytes": int(status.ullAvailPhys),
                    "total_bytes": int(status.ullTotalPhys),
                }
        except (AttributeError, OSError, ValueError):
            pass
    return {
        "reality": "OBSERVED_HOST",
        "platform": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
        "memory": memory,
        "home_disk": {"free_bytes": usage.free, "total_bytes": usage.total},
        "resource_reservation": "NONE",
    }


def execute(task_name: str) -> dict:
    if task_name not in ALLOWED_TASKS:
        raise ValueError("TASK_NOT_ALLOWED")
    if task_name == "status":
        return {
            "status": "READY",
            "agent_id": AGENT_ID,
            "resource_snapshot": resource_snapshot(),
            "execution_scope": "READ_ONLY",
        }
    if task_name == "platform":
        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        }
    return {"python": platform.python_version()}


def run_once(key: str) -> str:
    snapshot = resource_snapshot()
    memory = snapshot["memory"]
    metadata = {
        "platform": platform.system(),
        "model": platform.node(),
        "architecture": platform.machine(),
        "enrolled": True,
        "healthy": True,
        "capabilities": ["device.status", "device.info"],
        "cpu_cores": os.cpu_count() or 1,
        # The scheduler-facing capacity is currently available RAM, not total
        # installed RAM, so a memory-constrained host is not over-advertised.
        "memory_mb": int((memory["available_bytes"] or 0) / (1024 * 1024)),
        "total_memory_mb": int((memory["total_bytes"] or 0) / (1024 * 1024)),
        "disk_mb": int(snapshot["home_disk"]["free_bytes"] / (1024 * 1024)),
        "total_disk_mb": int(snapshot["home_disk"]["total_bytes"] / (1024 * 1024)),
        "resource_reality": "OBSERVED_HOST",
        "resource_reservation": "NONE",
    }
    request_json("POST", "/api/device/heartbeat", key, {"agent_id": AGENT_ID, "metadata": metadata})
    response = request_json("GET", "/api/device/poll?agent_id=" + quote(AGENT_ID, safe=""), key)
    task = response.get("task")
    if task is None:
        return "IDLE"
    if not isinstance(task, dict):
        raise RuntimeError("TASK_PAYLOAD_INVALID")
    task_id_value = task.get("task_id")
    task_name_value = task.get("task")
    if not isinstance(task_id_value, (str, int)) or isinstance(task_id_value, bool):
        raise RuntimeError("TASK_ID_INVALID")
    task_id = str(task_id_value).strip()
    if not task_id or len(task_id) > 200:
        raise RuntimeError("TASK_ID_INVALID")
    if not isinstance(task_name_value, str) or not task_name_value:
        raise RuntimeError("TASK_NAME_INVALID")
    task_name = task_name_value
    try:
        result = execute(task_name)
        report = {"task_id": task_id, "agent_id": AGENT_ID, "ok": True, "result": result, "error": ""}
    except (ValueError, OSError, RuntimeError) as exc:
        report = {"task_id": task_id, "agent_id": AGENT_ID, "ok": False, "result": {}, "error": str(exc)[:200]}
    request_json("POST", "/api/device/report", key, report)
    return "REPORTED:" + task_name


def main() -> int:
    validate_config()
    key = load_key()
    print("Electronic Brain Windows Bridge: outbound-only, read-only tasks")
    print("Credentials are not printed; stop with Ctrl+C.")
    while True:
        try:
            print(run_once(key))
        except KeyboardInterrupt:
            print("Windows Bridge stopped")
            return 0
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
            print("Bridge warning: " + type(exc).__name__ + " (details withheld)")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())

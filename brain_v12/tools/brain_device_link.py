#!/usr/bin/env python3
"""Electronic Brain device link agent for Windows and Android Termux.

Sends measured capacity heartbeats and polls only a tiny allowlist of safe
status tasks. It never runs arbitrary shell commands or network-supplied code.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def detect_platform() -> str:
    if os.environ.get("ANDROID_ROOT") or os.environ.get("TERMUX_VERSION"):
        return "android"
    if os.name == "nt":
        return "windows"
    return platform.system().lower() or "unknown"


def memory_mb() -> int:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
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

            state = MEMORYSTATUSEX()
            state.dwLength = ctypes.sizeof(state)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
                return int(state.ullTotalPhys // (1024 * 1024))
        except (AttributeError, OSError):
            pass
    return 0


def capacity_metadata() -> dict:
    kind = detect_platform()
    root = Path.home()
    try:
        disk_mb = shutil.disk_usage(str(root)).free // (1024 * 1024)
    except OSError:
        disk_mb = 0
    try:
        model = ""
        if kind == "android":
            model = subprocess.run(
                ["getprop", "ro.product.model"], capture_output=True,
                text=True, timeout=2, check=False,
            ).stdout.strip()[:100]
    except (OSError, subprocess.SubprocessError):
        model = ""
    return {
        "platform": kind,
        "hostname": socket.gethostname()[:100],
        "device_model": model,
        "cpu_cores": float(max(0, os.cpu_count() or 0)),
        "memory_mb": max(0, int(memory_mb())),
        "disk_mb": max(0, int(disk_mb)),
        "healthy": True,
        "capabilities": ["device.status", "device.info", "python.test"],
        "observation_only": True,
        "agent_version": "1.0.0",
    }


def post_heartbeat(base_url: str, agent_id: str, key: str, timeout: float = 12) -> dict:
    metadata = capacity_metadata()
    payload = json.dumps({"agent_id": agent_id, "metadata": metadata}).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/device/heartbeat",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-V12-Agent-Key": key,
            "X-V12-Agent-Id": agent_id,
            "User-Agent": "ElectronicBrain-DeviceLink/1.0.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(1024 * 64).decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else {}
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("heartbeat HTTP " + str(response.status))
            return {"ok": True, "http_status": response.status, "response": parsed, "metadata": metadata}
    except urllib.error.HTTPError as exc:
        # Never print headers or credentials.
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError("heartbeat HTTP " + str(exc.code) + ": " + detail) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("heartbeat network error: " + str(exc.reason)) from None



REMOTE_TASKS = {"status", "python_version", "platform"}


def execute_remote_task(name: str) -> dict:
    """Execute a fixed, read-only task; never interpret task parameters as code."""
    if name == "status":
        return {"status": "READY", "agent_version": "1.0.0", "metadata": capacity_metadata()}
    if name == "python_version":
        return {"python_version": platform.python_version(), "executable": sys.executable}
    if name == "platform":
        return {"platform": detect_platform(), "release": platform.release(), "machine": platform.machine()}
    raise ValueError("TASK_NOT_ALLOWED")


def request_json(base_url: str, path: str, agent_id: str, key: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json",
        "X-V12-Agent-Key": key,
        "X-V12-Agent-Id": agent_id,
        "User-Agent": "ElectronicBrain-DeviceLink/1.0.0",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base_url.rstrip("/") + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            raw = response.read(65536).decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError("HTTP " + str(exc.code) + ": " + detail) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("network error: " + str(exc.reason)) from None


def poll_and_run_one(base_url: str, agent_id: str, key: str) -> dict:
    from urllib.parse import quote
    polled = request_json(
        base_url, "/api/device/poll?agent_id=" + quote(agent_id, safe=""), agent_id, key
    )
    task = polled.get("task")
    if not isinstance(task, dict):
        return {"status": polled.get("status", "IDLE"), "task": None}
    task_id = str(task.get("task_id", ""))
    name = str(task.get("task", ""))
    try:
        if name not in REMOTE_TASKS:
            raise ValueError("TASK_NOT_ALLOWED")
        result = execute_remote_task(name)
        report = {"task_id": task_id, "agent_id": agent_id, "ok": True, "result": result, "error": ""}
    except Exception as exc:
        report = {"task_id": task_id, "agent_id": agent_id, "ok": False, "result": {}, "error": str(exc)[:500]}
    report_response = request_json(
        base_url, "/api/device/report", agent_id, key, method="POST", payload=report
    )
    return {"status": report_response.get("status", "REPORTED"), "task": name, "ok": report["ok"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="send one heartbeat, poll once, and exit")
    parser.add_argument("--interval", type=int, default=10, help="heartbeat interval seconds (minimum 5)")
    args = parser.parse_args()
    base_url = os.getenv("BRAIN_URL", "https://brain-control-plane-main.onrender.com").strip()
    agent_id = os.getenv("BRAIN_AGENT_ID", "").strip()
    key = os.getenv("BRAIN_AGENT_KEY", "").strip()
    kind = detect_platform()
    expected_prefix = {"android": "android-executor-", "windows": "windows-executor-"}.get(kind)
    if not agent_id or not key:
        print("CONFIG_ERROR: set BRAIN_AGENT_ID and BRAIN_AGENT_KEY in this device's environment.", file=sys.stderr)
        return 2
    if not base_url.startswith("https://"):
        print("CONFIG_ERROR: BRAIN_URL must use HTTPS.", file=sys.stderr)
        return 2
    if expected_prefix and not agent_id.startswith(expected_prefix):
        print("CONFIG_ERROR: " + kind + " agent ID must start with " + expected_prefix, file=sys.stderr)
        return 2
    interval = max(5, args.interval)
    while True:
        success = False
        try:
            result = post_heartbeat(base_url, agent_id, key)
            m = result["metadata"]
            poll_result = poll_and_run_one(base_url, agent_id, key)
            print(json.dumps({
                "ok": True, "agent_id": agent_id, "platform": m["platform"],
                "cpu_cores": m["cpu_cores"], "memory_mb": m["memory_mb"],
                "disk_mb": m["disk_mb"], "http_status": result["http_status"],
                "status": result["response"].get("status", "UNKNOWN"),
                "poll": poll_result,
            }, ensure_ascii=False), flush=True)
            success = True
        except Exception as exc:
            print(json.dumps({"ok": False, "agent_id": agent_id, "error": str(exc)}, ensure_ascii=False), file=sys.stderr, flush=True)
        if args.once:
            return 0 if success else 1
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())

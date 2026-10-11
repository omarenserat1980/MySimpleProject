#!/usr/bin/env python3
"""Electronic Brain device link agent for Windows and Android Termux.

Sends authenticated, measured capacity heartbeats only. This agent does not poll
or claim queued tasks, so it cannot steal work intended for another executor.
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="send one authenticated capacity heartbeat and exit")
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
            print(json.dumps({
                "ok": True, "agent_id": agent_id, "platform": m["platform"],
                "cpu_cores": m["cpu_cores"], "memory_mb": m["memory_mb"],
                "disk_mb": m["disk_mb"], "http_status": result["http_status"],
                "status": result["response"].get("status", "UNKNOWN"),
                "poll": "DISABLED_OBSERVATION_ONLY",
            }, ensure_ascii=False), flush=True)
            success = True
        except Exception as exc:
            print(json.dumps({"ok": False, "agent_id": agent_id, "error": str(exc)}, ensure_ascii=False), file=sys.stderr, flush=True)
        if args.once:
            return 0 if success else 1
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())

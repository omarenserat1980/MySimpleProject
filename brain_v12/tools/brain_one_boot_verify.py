#!/usr/bin/env python3
"""Read-only health proof for Brain One-Boot."""
from __future__ import annotations
import json, os, sys, time, urllib.request

base = os.environ.get("V12_BRAIN_URL", "http://127.0.0.1:8012").rstrip("/")
checks = {}

try:
    with urllib.request.urlopen(base + "/health", timeout=4) as r:
        checks["runtime"] = r.status == 200
except Exception as exc:
    checks["runtime"] = False
    checks["runtime_error"] = str(exc)[:160]

try:
    with urllib.request.urlopen(base + "/api/device/status", timeout=4) as r:
        data = json.loads(r.read().decode())
    checks["device_registry"] = bool(data.get("ok"))
    agents = data.get("agents", {}).get("agents", [])
    checks["termux_online"] = any(a.get("agent_id") == "redmi3-01" and a.get("online") for a in agents)
    checks["android_online"] = any(a.get("agent_id") == "android-executor-redmi3-01" and a.get("online") for a in agents)
    checks["queue_empty"] = int(data.get("queued", 0)) == 0 and int(data.get("pending", 0)) == 0
    checks["completed"] = int(data.get("completed", 0))
    checks["failed"] = int(data.get("failed", 0))
except Exception as exc:
    checks["device_registry"] = False
    checks["status_error"] = str(exc)[:160]

checks["timestamp"] = time.time()
print("BRAIN_ONE_BOOT_VERIFY " + json.dumps(checks, ensure_ascii=False, separators=(",", ":")))
sys.exit(0 if checks.get("runtime") and checks.get("device_registry") else 1)

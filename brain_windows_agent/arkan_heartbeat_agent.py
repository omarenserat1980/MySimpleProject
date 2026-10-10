#!/usr/bin/env python3
"""Outbound-only read-only heartbeat agent for Arkan. No task execution."""
from __future__ import annotations
import argparse, ctypes, json, os, platform, random, signal, sys, time
import urllib.error, urllib.parse, urllib.request
from pathlib import Path
from typing import Any

AGENT_VERSION = "1.0.0"
DEFAULT_AGENT_ID = "arkan-windows-agent-01"
STOP = False

def validate_brain_url(value: str) -> str:
    value = value.strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
        raise ValueError("BRAIN_URL_MUST_USE_HTTPS_UNLESS_LOOPBACK")
    if not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("BRAIN_URL_INVALID")
    return value

def memory_snapshot() -> dict[str, int] | None:
    if os.name != "nt":
        return None
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
          ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
          ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
          ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
          ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return {"total_ram_mib": int(status.ullTotalPhys / (1024 ** 2)),
            "available_ram_mib": int(status.ullAvailPhys / (1024 ** 2)),
            "memory_load_percent": int(status.dwMemoryLoad)}

def build_metadata() -> dict[str, Any]:
    return {"agent_version": AGENT_VERSION, "platform": platform.platform(),
      "os_name": platform.system(), "os_release": platform.release(),
      "python_version": platform.python_version(), "logical_cpus": os.cpu_count() or 0,
      "memory": memory_snapshot(), "capabilities": ["heartbeat", "readonly_host_metadata"],
      "identity_verified": False, "execution_eligible": False, "task_execution_enabled": False}

def post_heartbeat(brain_url: str, agent_id: str, key: str, timeout: float = 10) -> dict[str, Any]:
    body = json.dumps({"agent_id": agent_id, "metadata": build_metadata()}).encode("utf-8")
    request = urllib.request.Request(brain_url + "/api/device/heartbeat", data=body,
      headers={"Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": f"ElectronicBrain-Arkan-Agent/{AGENT_VERSION}",
        "X-V12-Agent-Key": key, "X-V12-Agent-Id": agent_id}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"HEARTBEAT_HTTP_STATUS_{response.status}")
        payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise RuntimeError("HEARTBEAT_NOT_ACKNOWLEDGED")
        return payload

def read_key(path: Path) -> str:
    try:
        key = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError("AGENT_KEY_FILE_UNAVAILABLE") from exc
    if len(key) < 32:
        raise RuntimeError("AGENT_KEY_TOO_SHORT")
    return key

def request_stop(_signum: int, _frame: Any) -> None:
    global STOP
    STOP = True

def run(brain_url: str, agent_id: str, key_file: Path, interval: int, max_backoff: int) -> int:
    key = read_key(key_file)
    delay = 1
    while not STOP:
        try:
            result = post_heartbeat(brain_url, agent_id, key)
            print(json.dumps({"event": "heartbeat_ok", "agent_id": agent_id,
              "server_status": result.get("status", "ACK"), "utc_epoch": int(time.time())}), flush=True)
            delay = 1
            end = time.monotonic() + interval
            while not STOP and time.monotonic() < end:
                time.sleep(min(1.0, max(0.0, end - time.monotonic())))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
            wait = max(1, int(min(max_backoff, delay) * random.uniform(0.8, 1.2)))
            print(json.dumps({"event": "heartbeat_retry", "agent_id": agent_id,
              "error_type": type(exc).__name__, "retry_in_seconds": wait,
              "utc_epoch": int(time.time())}), flush=True)
            end = time.monotonic() + wait
            while not STOP and time.monotonic() < end:
                time.sleep(min(1.0, max(0.0, end - time.monotonic())))
            delay = min(max_backoff, max(2, delay * 2))
    print(json.dumps({"event": "agent_stopped", "agent_id": agent_id}), flush=True)
    return 0

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brain-url", default=os.getenv("BRAIN_URL", ""))
    parser.add_argument("--agent-id", default=os.getenv("BRAIN_AGENT_ID", DEFAULT_AGENT_ID))
    parser.add_argument("--key-file", default=os.getenv("BRAIN_WINDOWS_AGENT_KEY_FILE",
      r"C:\ProgramData\Brain\secrets\agent.key"))
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--max-backoff", type=int, default=120)
    args = parser.parse_args()
    try:
        brain_url = validate_brain_url(args.brain_url)
        if not 5 <= args.interval <= 300: raise ValueError("INTERVAL_MUST_BE_5_TO_300_SECONDS")
        if not 10 <= args.max_backoff <= 600: raise ValueError("MAX_BACKOFF_MUST_BE_10_TO_600_SECONDS")
        key_file = Path(args.key_file)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"): signal.signal(signal.SIGTERM, request_stop)
    return run(brain_url, args.agent_id, key_file, args.interval, args.max_backoff)

if __name__ == "__main__":
    raise SystemExit(main())

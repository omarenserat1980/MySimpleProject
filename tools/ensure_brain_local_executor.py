#!/usr/bin/env python3
"""Ensure the Brain-owned local executor supervisor is running and prove heartbeat.

This launcher is a repair utility only. It never changes the autonomy result.
It starts the supervisor when needed, then waits for a fresh heartbeat. If the
worker cannot start, it returns the supervisor log as failure evidence.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "brain_v12" / "local_worker" / "brain_local_supervisor.py"
ARTIFACTS = ROOT / "brain6_artifacts" / "local_worker"
PID_FILE = ARTIFACTS / "supervisor.pid"
LOG_FILE = ARTIFACTS / "supervisor.log"
STATE_FILE = ARTIFACTS / "launcher.json"
HEARTBEAT = ARTIFACTS / "heartbeat.json"
WAIT_SECONDS = max(5.0, float(os.environ.get("BRAIN_EXECUTOR_STARTUP_WAIT_SECONDS", "15")))


def running_pid(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def find_existing() -> int | None:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if running_pid(pid):
                return pid
        except (ValueError, OSError):
            pass
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "brain_v12/local_worker/brain_local_supervisor.py"],
            text=True, stderr=subprocess.DEVNULL,
        )
        for item in out.split():
            try:
                pid = int(item)
                if pid != os.getpid() and running_pid(pid):
                    return pid
            except ValueError:
                continue
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return None


def heartbeat_is_fresh(max_age: float = 15.0) -> bool:
    try:
        age = time.time() - HEARTBEAT.stat().st_mtime
        return age <= max_age
    except OSError:
        return False


def log_tail(limit: int = 12000) -> str:
    try:
        return LOG_FILE.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError as exc:
        return f"log_unavailable:{type(exc).__name__}:{exc}"


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    existing = find_existing()
    started = False
    if existing is None:
        log = LOG_FILE.open("a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(SUPERVISOR)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        PID_FILE.write_text(str(proc.pid), encoding="utf-8")
        existing = proc.pid
        started = True
        log.close()

    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        if heartbeat_is_fresh():
            result = {
                "schema": "brain.local_executor_launcher.v2",
                "status": "READY",
                "supervisor_pid": existing,
                "started_by_launcher": started,
                "heartbeat": str(HEARTBEAT),
            }
            STATE_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2))
            return 0
        time.sleep(0.5)

    result = {
        "schema": "brain.local_executor_launcher.v2",
        "status": "FAILED",
        "reason": "fresh_heartbeat_not_observed",
        "supervisor_pid": existing,
        "started_by_launcher": started,
        "heartbeat": str(HEARTBEAT),
        "log_tail": log_tail(),
    }
    STATE_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

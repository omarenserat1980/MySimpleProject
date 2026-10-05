#!/usr/bin/env python3
"""Ensure the Brain-owned local executor supervisor is running.

This is a repair/launcher utility only. It never changes the autonomy result
and never treats a stale heartbeat as proof of readiness.
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
    # Avoid spawning duplicates when the PID file was lost.
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", "brain_v12/local_worker/brain_local_supervisor.py"],
            text=True,
            stderr=subprocess.DEVNULL,
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


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    existing = find_existing()
    if existing:
        result = {"schema": "brain.local_executor_launcher.v1",
                  "status": "ALREADY_RUNNING", "supervisor_pid": existing}
        STATE_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0

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
    result = {"schema": "brain.local_executor_launcher.v1",
              "status": "STARTED", "supervisor_pid": proc.pid,
              "heartbeat_expected": str(ARTIFACTS / "heartbeat.json")}
    STATE_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

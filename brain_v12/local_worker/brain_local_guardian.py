#!/usr/bin/env python3
"""Defensive guardian for the Brain local executor.

Provider-free, stdlib-only supervision:
- launches the worker as a Python module
- injects repository PYTHONPATH
- distinguishes crash from stale heartbeat
- applies startup grace and exponential backoff
- records durable incident receipts
- stops crash loops instead of hammering the device
"""
from __future__ import annotations
import json, os, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "brain6_artifacts" / "local_worker"
HB = ART / "heartbeat.json"
RECEIPTS = ART / "guardian_receipts.jsonl"
STATE = ART / "guardian.json"
LOG = ART / "guardian.log"
MODULE = "brain_v12.local_worker.brain_local_worker"

STARTUP_GRACE = max(3.0, float(os.getenv("BRAIN_GUARDIAN_STARTUP_GRACE_SECONDS", "20")))
STALE_AFTER = max(5.0, float(os.getenv("BRAIN_GUARDIAN_STALE_SECONDS", "35")))
POLL = max(0.5, float(os.getenv("BRAIN_GUARDIAN_POLL_SECONDS", "2")))
BACKOFF_MAX = max(5.0, float(os.getenv("BRAIN_GUARDIAN_BACKOFF_MAX_SECONDS", "60")))
MAX_RESTARTS = max(1, int(os.getenv("BRAIN_GUARDIAN_MAX_RESTARTS", "8")))
WINDOW = max(10.0, float(os.getenv("BRAIN_GUARDIAN_RESTART_WINDOW_SECONDS", "300")))

def now():
    return datetime.now(timezone.utc).isoformat()

def append_receipt(event, **data):
    ART.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": now(), "event": event, **data}, ensure_ascii=False) + "\n")

def write_state(**data):
    ART.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schema":"brain.local_guardian.v1", **data}, indent=2), encoding="utf-8")
    tmp.replace(STATE)

def fresh_heartbeat(expected_pid=None, started_at=None):
    try:
        payload = json.loads(HB.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(str(payload["timestamp"]))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        pid = int(payload.get("pid", 0))
        valid = age <= STALE_AFTER and pid > 0
        if expected_pid is not None:
            valid = valid and pid == expected_pid
        if started_at is not None:
            valid = valid and ts.timestamp() >= started_at
        return valid, round(age, 3), payload
    except Exception as exc:
        return False, None, {"error": f"{type(exc).__name__}:{exc}"}

def terminate(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        deadline = time.time() + 5
        while time.time() < deadline and proc.poll() is None:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        try:
            proc.kill()
        except OSError:
            pass

def launch():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH","")
    log = LOG.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", MODULE],
        cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
        stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log.close()
    return proc

def main():
    ART.mkdir(parents=True, exist_ok=True)
    restart_times = []
    backoff = 1.0
    proc = None
    while True:
        if proc is None:
            proc = launch()
            started = time.time()
            append_receipt("worker_started", pid=proc.pid)
            write_state(status="STARTING", worker_pid=proc.pid, restart_count=len(restart_times))
            while time.time() - started < STARTUP_GRACE:
                if proc.poll() is not None:
                    code = proc.returncode
                    append_receipt("worker_crashed_during_startup", pid=proc.pid, returncode=code)
                    proc = None
                    break
                ok, age, _ = fresh_heartbeat(expected_pid=proc.pid, started_at=started)
                if ok:
                    backoff = 1.0
                    write_state(status="READY", worker_pid=proc.pid, heartbeat_age_seconds=age,
                                 restart_count=len(restart_times))
                    break
                time.sleep(POLL)
            if proc is None:
                pass
            else:
                ok, age, _ = fresh_heartbeat(expected_pid=proc.pid, started_at=started)
                if not ok:
                    append_receipt("startup_heartbeat_timeout", pid=proc.pid, heartbeat_age_seconds=age)
                    terminate(proc)
                    proc = None

        if proc is None:
            cutoff = time.time() - WINDOW
            restart_times[:] = [t for t in restart_times if t >= cutoff]
            if len(restart_times) >= MAX_RESTARTS:
                append_receipt("crash_loop_blocked", restarts=len(restart_times), window_seconds=WINDOW)
                write_state(status="BLOCKED_CRASH_LOOP", restart_count=len(restart_times))
                return 2
            restart_times.append(time.time())
            write_state(status="BACKOFF", restart_count=len(restart_times), backoff_seconds=backoff)
            time.sleep(backoff)
            backoff = min(BACKOFF_MAX, backoff * 2)
            continue

        if proc.poll() is not None:
            code = proc.returncode
            append_receipt("worker_exit", pid=proc.pid, returncode=code)
            proc = None
            continue

        ok, age, payload = fresh_heartbeat(expected_pid=proc.pid)
        if not ok:
            append_receipt("heartbeat_stale", pid=proc.pid, heartbeat_age_seconds=age, heartbeat=payload)
            terminate(proc)
            proc = None
            continue

        write_state(status="READY", worker_pid=proc.pid, heartbeat_age_seconds=age,
                    restart_count=len(restart_times))
        time.sleep(POLL)

if __name__ == "__main__":
    raise SystemExit(main())

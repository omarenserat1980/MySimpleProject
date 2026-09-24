#!/usr/bin/env python3
"""V12 Termux Agent: poll Brain Gateway, execute allowlisted smoke-test tasks, report results."""
from __future__ import annotations
import os
import platform
import subprocess
import time
import requests

BRAIN_URL = os.environ["BRAIN_URL"].rstrip("/")
AGENT_KEY = os.environ["TERMUX_AGENT_KEY"]
AGENT_ID = os.getenv("TERMUX_AGENT_ID", "android-termux-v12")
POLL_SECONDS = max(1, int(os.getenv("TERMUX_POLL_SECONDS", "2")))

def headers():
    return {"X-V12-Agent-Key": AGENT_KEY}

def execute(task, params):
    if task == "python_version":
        p = subprocess.run(["python", "--version"], capture_output=True, text=True, timeout=20)
        output = (p.stdout or p.stderr).strip()
        return p.returncode == 0, {
            "stdout": output,
            "stderr": (p.stderr or "").strip(),
            "returncode": p.returncode,
        }, ""

    if task == "termux_path":
        p = subprocess.run(["pwd"], capture_output=True, text=True, timeout=10)
        return p.returncode == 0, {
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
            "returncode": p.returncode,
        }, ""

    if task == "platform":
        return True, {
            "platform": platform.platform(),
            "python": platform.python_version(),
        }, ""

    if task == "status":
        return True, {
            "agent_id": AGENT_ID,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "status": "READY",
        }, ""

    return False, {}, "TASK_NOT_ALLOWED"

def main():
    print(f"[V12-Agent] READY id={AGENT_ID}")
    while True:
        try:
            r = requests.get(
                f"{BRAIN_URL}/api/device/poll",
                params={"agent_id": AGENT_ID},
                headers=headers(),
                timeout=30,
            )
            r.raise_for_status()
            payload = r.json()
            task = payload.get("task")
            if not task:
                time.sleep(POLL_SECONDS)
                continue

            task_id = task["task_id"]
            task_name = task["task"]
            print(f"[V12-Agent] CLAIMED {task_id} {task_name}")

            try:
                ok, result, error = execute(task_name, task.get("params", {}))
            except Exception as exc:
                ok, result, error = False, {}, f"{type(exc).__name__}: {exc}"

            report = {
                "task_id": task_id,
                "agent_id": AGENT_ID,
                "ok": ok,
                "result": result,
                "error": error,
            }
            rr = requests.post(
                f"{BRAIN_URL}/api/device/report",
                json=report,
                headers=headers(),
                timeout=30,
            )
            rr.raise_for_status()
            print(f"[V12-Agent] REPORTED {task_id} ok={ok}")
        except KeyboardInterrupt:
            print("\n[V12-Agent] STOPPED")
            return
        except Exception as exc:
            print(f"[V12-Agent] ERROR {type(exc).__name__}: {exc}")
            time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()

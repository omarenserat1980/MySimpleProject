#!/usr/bin/env python3
"""V12 Brain Termux Emulator Agent for Electronic Brain.

GitHub is the control-plane contract. Runtime execution remains provider-agnostic.
This agent is the Brain-owned Android/Termux execution bridge and exposes only
allowlisted Brain operations.
"""
from __future__ import annotations
import os
import platform
import subprocess
import time
import json
import urllib.parse
import urllib.request
from pathlib import Path

BRAIN_URL = os.environ["BRAIN_URL"].rstrip("/")
AGENT_KEY = os.environ["BRAIN_EMULATOR_KEY"]
AGENT_ID = os.getenv("BRAIN_EMULATOR_ID", "android-brain-emulator-v12")
MAX_TASKS_PER_RUN = max(1, int(os.getenv("BRAIN_EMULATOR_MAX_TASKS_PER_RUN", "100")))
STOP_ON_ERROR = os.getenv("BRAIN_EMULATOR_STOP_ON_ERROR", "false").lower() == "true"
POLL_SECONDS = max(1, int(os.getenv("BRAIN_EMULATOR_POLL_SECONDS", "2")))
HEARTBEAT_SECONDS = max(5, int(os.getenv("BRAIN_EMULATOR_HEARTBEAT_SECONDS", "10")))
REQUEST_TIMEOUT = max(5, int(os.getenv("BRAIN_EMULATOR_REQUEST_TIMEOUT", "30")))
ROOT = Path(__file__).resolve().parent.parent

def request(method, path, payload=None, params=None):
    url = f"{BRAIN_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    hdrs = {"X-V12-Agent-Key": AGENT_KEY}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))

def execute(task, params):
    if task == "python_version":
        p = subprocess.run(["python", "--version"], capture_output=True, text=True, timeout=20)
        output = (p.stdout or p.stderr).strip()
        return p.returncode == 0, {"stdout": output, "stderr": (p.stderr or "").strip(), "returncode": p.returncode}, ""

    if task == "brain_home":
        p = subprocess.run(["pwd"], capture_output=True, text=True, timeout=10)
        return p.returncode == 0, {"stdout": p.stdout.strip(), "stderr": p.stderr.strip(), "returncode": p.returncode}, ""

    if task == "platform":
        return True, {"platform": platform.platform(), "python": platform.python_version()}, ""

    if task == "brain_local_painter_draw":
        prompt = str(params.get("prompt", "")).strip()
        if not prompt:
            return False, {}, "PROMPT_REQUIRED"
        import sys
        sys.path.insert(0, str(ROOT))
        from brain_v12.brain.draw_gateway import draw_local
        result = draw_local(prompt)
        if not result.get("ok") or not result.get("verified") or not result.get("svg"):
            return False, {"result": result}, "BRAIN_LOCAL_PAINTER_FAILED"
        out_dir = ROOT / "brain6_artifacts" / "local_painter"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in prompt[:40]).strip("_") or "scene"
        out = out_dir / f"{int(time.time())}-{safe_id}.svg"
        out.write_text(result["svg"], encoding="utf-8")
        return True, {
            "provider": "brain_local_painter",
            "verified": True,
            "prompt": prompt,
            "artifact": str(out),
            "format": "svg",
            "scene": result.get("scene", {}),
            "svg": result["svg"],
        }, ""

    if task == "cinematic_factory_run":
        script = ROOT / "brain_emulator_agent" / "cinematic_factory.py"
        p = subprocess.run(["python", str(script)], cwd=str(ROOT), capture_output=True,
                           text=True, timeout=24 * 60 * 60)
        return p.returncode == 0, {
            "stdout": p.stdout[-8000:], "stderr": p.stderr[-4000:], "returncode": p.returncode,
            "root": str(ROOT),
        }, "" if p.returncode == 0 else "CINEMATIC_FACTORY_FAILED"

    if task == "cinematic_room13_render":
        script = ROOT / "brain_v12" / "movie_summary_factory" / "render_room13_animatic.py"
        if not script.exists():
            return False, {}, "ROOM13_RENDER_SCRIPT_NOT_FOUND"
        p = subprocess.run(["python", str(script)], cwd=str(ROOT), capture_output=True,
                           text=True, timeout=24 * 60 * 60)
        return p.returncode == 0, {
            "stdout": p.stdout[-12000:], "stderr": p.stderr[-6000:], "returncode": p.returncode,
            "root": str(ROOT), "script": str(script),
        }, "" if p.returncode == 0 else "CINEMATIC_ROOM13_RENDER_FAILED"

    if task == "status":
        return True, {"agent_id": AGENT_ID, "platform": platform.platform(),
                      "python": platform.python_version(), "status": "READY"}, ""

    return False, {}, "TASK_NOT_ALLOWED"

def main():
    print(f"[Brain-Termux] READY id={AGENT_ID}")
    completed = 0
    last_heartbeat = 0.0
    while completed < MAX_TASKS_PER_RUN:
        try:
            now = time.time()
            if now - last_heartbeat >= HEARTBEAT_SECONDS:
                try:
                    request("POST", "/api/device/heartbeat", payload={"agent_id": AGENT_ID})
                except Exception as heartbeat_error:
                    print(f"[Brain-Termux] HEARTBEAT_FAILURE: {heartbeat_error}")
                last_heartbeat = now
            payload = request("GET", "/api/device/poll", params={"agent_id": AGENT_ID})
            task = payload.get("task")
            if not task:
                time.sleep(POLL_SECONDS)
                continue
            task_id = task["task_id"]
            task_name = task["task"]
            print(f"[Brain-Termux] CLAIMED {task_id} {task_name}")
            try:
                ok, result, error = execute(task_name, task.get("params", {}))
            except Exception as exc:
                ok, result, error = False, {}, f"{type(exc).__name__}: {exc}"
            report = {"task_id": task_id, "agent_id": AGENT_ID, "ok": ok,
                      "result": result, "error": error}
            request("POST", "/api/device/report", payload=report)
            print(f"[Brain-Termux] REPORTED {task_id} ok={ok}")
            completed += 1
            if STOP_ON_ERROR and not ok:
                return
        except KeyboardInterrupt:
            print("\n[Brain-Termux] STOPPED")
            return
        except Exception as exc:
            print(f"[Brain-Termux] ERROR {type(exc).__name__}: {exc}")
            time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()

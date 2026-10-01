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
from uuid import uuid4

BRAIN_URL = (os.getenv("BRAIN_URL") or os.getenv("V12_BRAIN_URL") or "").rstrip("/")
KEY_FILE = os.getenv("BRAIN_EMULATOR_KEY_FILE") or os.getenv("V12_AGENT_KEY_FILE") or ""
AGENT_KEY = (os.getenv("BRAIN_EMULATOR_KEY") or os.getenv("V12_AGENT_KEY") or "").strip()
if not AGENT_KEY and KEY_FILE:
    try:
        AGENT_KEY = Path(KEY_FILE).expanduser().read_text(encoding="utf-8").strip()
    except OSError:
        pass
AGENT_ID = os.getenv("BRAIN_EMULATOR_ID") or os.getenv("V12_AGENT_ID") or ("agent-" + uuid4().hex[:12])
MAX_TASKS_PER_RUN = max(1, int(os.getenv("BRAIN_EMULATOR_MAX_TASKS_PER_RUN", "100")))
STOP_ON_ERROR = os.getenv("BRAIN_EMULATOR_STOP_ON_ERROR", "false").lower() == "true"
POLL_SECONDS = max(1, int(os.getenv("BRAIN_EMULATOR_POLL_SECONDS") or os.getenv("V12_POLL_SECONDS") or "5"))
HEARTBEAT_SECONDS = max(5, int(os.getenv("BRAIN_EMULATOR_HEARTBEAT_SECONDS", "10")))
REQUEST_TIMEOUT = max(5, int(os.getenv("BRAIN_EMULATOR_REQUEST_TIMEOUT", "30")))
ROOT = Path(__file__).resolve().parent.parent

def request(method, path, payload=None, params=None):
    if not BRAIN_URL:
        raise RuntimeError("BRAIN_URL_OR_V12_BRAIN_URL_REQUIRED")
    if not AGENT_KEY:
        raise RuntimeError("BRAIN_EMULATOR_KEY_OR_V12_AGENT_KEY_REQUIRED")
    url = f"{BRAIN_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    hdrs = {"X-V12-Agent-Key": AGENT_KEY, "X-V12-Agent-Id": AGENT_ID, "User-Agent": "Brain-Termux-Emulator/1.0"}
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
        if not result.get("ok") or not result.get("verified") or not result.get("png_base64"):
            return False, {"result": result}, "BRAIN_LOCAL_PAINTER_FAILED"
        import base64
        out_dir = ROOT / "brain6_artifacts" / "local_painter"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in prompt[:40]).strip("_") or "scene"
        out = out_dir / f"{int(time.time())}-{safe_id}.png"
        out.write_bytes(base64.b64decode(result["png_base64"], validate=True))
        return True, {
            "provider": "brain_local_machine_raster",
            "verified": True,
            "prompt": prompt,
            "artifact": str(out),
            "format": "png",
            "renderer": "machine-raster",
            "machine_commands": result.get("machine_commands", []),
            "scene": result.get("scene", {}),
            "png_base64": result["png_base64"],
        }, ""

    if task == "brain_cpp_raster_test":
        src = ROOT / "brain_v12" / "native" / "brain_raster_cpp"
        build = src / "build"
        out = ROOT / "brain6_artifacts" / "cpp_raster" / "brain-raster.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        cmake = subprocess.run(["cmake","-S",str(src),"-B",str(build)], capture_output=True,text=True,timeout=120)
        if cmake.returncode != 0:
            return False, {"stdout":cmake.stdout[-4000:],"stderr":cmake.stderr[-4000:]}, "CPP_CMAKE_FAILED"
        build_run = subprocess.run(["cmake","--build",str(build),"--config","Release"], capture_output=True,text=True,timeout=600)
        if build_run.returncode != 0:
            return False, {"stdout":build_run.stdout[-4000:],"stderr":build_run.stderr[-4000:]}, "CPP_BUILD_FAILED"
        exe = build / "brain_raster"
        if not exe.exists(): exe = build / "Release" / "brain_raster"
        run = subprocess.run([str(exe),str(out)],capture_output=True,text=True,timeout=120)
        ok = run.returncode == 0 and out.exists() and out.stat().st_size > 128
        return ok, {"verified":ok,"artifact":str(out),"stdout":run.stdout,"stderr":run.stderr}, "" if ok else "CPP_RASTER_FAILED"

    if task == "brain_machine_cinema_60m":
        title = str(params.get("title", "BRAIN — فيلم الآلة")).strip()
        script = ROOT / "brain_v12" / "machine_cinematic_factory.py"
        env = os.environ.copy()
        env["BRAIN_FILM_TITLE"] = title
        p = subprocess.run(["python", str(script)], cwd=str(ROOT), env=env,
                           capture_output=True, text=True, timeout=24 * 60 * 60)
        artifact = ROOT / "brain6_artifacts" / "machine_films" / "final.mp4"
        manifest = ROOT / "brain6_artifacts" / "machine_films" / "manifest.json"
        ok = p.returncode == 0 and artifact.exists() and manifest.exists()
        return ok, {"status":"VERIFIED_COMPLETED" if ok else "FAILED",
                     "title":title,"stdout":p.stdout[-12000:],"stderr":p.stderr[-6000:],
                     "artifact":str(artifact),"manifest":str(manifest),
                     "returncode":p.returncode}, "" if ok else "BRAIN_MACHINE_CINEMA_FAILED"

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
                    request("POST", "/api/device/heartbeat", payload={"agent_id": AGENT_ID, "metadata": {"platform": platform.platform(), "python": platform.python_version()}})
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

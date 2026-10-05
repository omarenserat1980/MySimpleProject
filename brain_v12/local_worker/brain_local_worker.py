#!/usr/bin/env python3
"""Safe filesystem-backed execution adapter for Brain.

The worker is provider-free and allowlisted. It can execute the Brain Local
Painter without external image APIs.
"""
from __future__ import annotations
import json, os, platform, shutil, subprocess, time, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.environ.get("BRAIN_LOCAL_WORKER_ROOT", "brain6_artifacts/local_worker"))
QUEUED, RUNNING, COMPLETED, FAILED = (ROOT / x for x in ("queued", "running", "completed", "failed"))
WORKER_ID = os.environ.get("BRAIN_WORKER_ID", "brain-local-01")
POLL = max(1.0, float(os.environ.get("BRAIN_LOCAL_WORKER_POLL_SECONDS", "2")))

def utc():
    return datetime.now(timezone.utc).isoformat()

def setup():
    for p in (QUEUED, RUNNING, COMPLETED, FAILED):
        p.mkdir(parents=True, exist_ok=True)

def safe_command_version(binary: str):
    path = shutil.which(binary)
    if not path:
        return {"available": False, "binary": binary}
    out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
    return {"available": out.returncode == 0, "binary": binary,
            "version": (out.stdout or out.stderr).splitlines()[0][:300]}

CI_PROFILES = {
    "runner_policy": ("tests/test_execution_policy.py", "tests/test_runner_policy_audit.py"),
    "foundation": ("tests/test_platform_foundation.py", "tests/test_brain_supervisor_bridge.py"),
    "autonomous_pipeline": ("tests/test_autonomous_pipeline.py",),
}

def execute(task: str, params: dict):
    if task == "brain_ci_verify":
        profile = str(params.get("profile", "")).strip()
        if profile not in CI_PROFILES:
            raise ValueError(f"unknown_ci_profile:{profile}")
        root = Path(__file__).resolve().parents[2]
        tests = [str(root / item) for item in CI_PROFILES[profile]]
        started = time.monotonic()
        p = subprocess.run([sys.executable, "-m", "pytest", "-q", *tests],
                           cwd=str(root), capture_output=True, text=True)
        duration = round(time.monotonic() - started, 6)
        return {
            "provider": "brain_local_ci",
            "profile": profile,
            "verified": p.returncode == 0,
            "status": "VERIFIED" if p.returncode == 0 else "FAILED",
            "exit_code": p.returncode,
            "duration_seconds": duration,
            "stdout": p.stdout[-12000:],
            "stderr": p.stderr[-12000:],
        }
    if task == "python_version":
        return {"python": platform.python_version()}
    if task == "platform":
        return {"system": platform.system(), "release": platform.release(), "machine": platform.machine()}
    if task == "brain_home":
        return {"cwd": str(Path.cwd()), "home": str(Path.home())}
    if task == "ffmpeg_version":
        return safe_command_version("ffmpeg")
    if task == "ffprobe_version":
        return safe_command_version("ffprobe")
    if task == "filesystem_probe":
        usage = shutil.disk_usage(Path.cwd())
        return {"free_bytes": usage.free, "total_bytes": usage.total}
    if task in ("brain_machine_cinema_60m", "brain_machine_cinema_120m"):
        import subprocess
        title = str(params.get("title", "BRAIN — فيلم الآلة")).strip()
        env = os.environ.copy()
        env["BRAIN_FILM_TITLE"] = title
        script = Path(__file__).resolve().parents[1] / "machine_cinematic_factory.py"
        p = subprocess.run([sys.executable, str(script)], cwd=str(Path(__file__).resolve().parents[2]),
                           env=env, capture_output=True, text=True, timeout=24*60*60)
        if p.returncode != 0:
            raise RuntimeError("machine_cinema_failed:" + (p.stderr or p.stdout)[-4000:])
        return {"provider":"brain_machine_cinema","verified":True,"status":"VERIFIED_COMPLETED",
                "title":title,"stdout":p.stdout[-8000:],"artifact":str(Path(env.get("BRAIN_MACHINE_FILM_ROOT", Path.cwd()/"brain6_artifacts"/"machine_films"))/"final.mp4"),
                "manifest":str(Path(env.get("BRAIN_MACHINE_FILM_ROOT", Path.cwd()/"brain6_artifacts"/"machine_films"))/"manifest.json")}

    if task == "brain_local_painter_draw":
        prompt = str(params.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("prompt_required")
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from brain_v12.brain.draw_gateway import draw_local
        result = draw_local(prompt)
        if not result.get("ok") or not result.get("verified") or not result.get("png_base64"):
            raise ValueError("brain_local_painter_failed")
        import base64
        out_dir = Path.cwd() / "brain6_artifacts" / "local_painter"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{int(time.time())}-scene.png"
        out.write_bytes(base64.b64decode(result["png_base64"], validate=True))
        return {"provider": "brain_local_machine_raster", "verified": True,
                "prompt": prompt, "artifact": str(out), "format": "png",
                "renderer": "machine-raster",
                "machine_commands": result.get("machine_commands", []),
                "scene": result.get("scene", {})}
    raise ValueError(f"task_not_allowlisted:{task}")

def process(path: Path):
    claimed = RUNNING / path.name
    try:
        path.replace(claimed)
    except FileNotFoundError:
        return
    started = utc()
    try:
        job = json.loads(claimed.read_text(encoding="utf-8"))
        task = job.get("task")
        if not isinstance(task, str):
            raise ValueError("task_required")
        result = {"job_id": job.get("job_id", claimed.stem), "worker_id": WORKER_ID,
                  "status": "VERIFIED", "started_at": started, "completed_at": utc(),
                  "evidence": execute(task, job.get("params", {}))}
        (COMPLETED / claimed.name).write_text(json.dumps(result, indent=2), encoding="utf-8")
        claimed.unlink(missing_ok=True)
    except Exception as exc:
        result = {"job_id": claimed.stem, "worker_id": WORKER_ID, "status": "FAILED",
                  "started_at": started, "completed_at": utc(),
                  "error": f"{type(exc).__name__}:{exc}"}
        (FAILED / claimed.name).write_text(json.dumps(result, indent=2), encoding="utf-8")
        claimed.unlink(missing_ok=True)

def main():
    setup()
    print(f"Brain Local Worker {WORKER_ID} -> {ROOT}")
    while True:
        for path in sorted(QUEUED.glob("*.json")):
            process(path)
        time.sleep(POLL)

if __name__ == "__main__":
    main()

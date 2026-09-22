"""Small HTTP gateway for a self-hosted Wan2.1 installation.

Run this service on the GPU machine that has Wan2.1 and its checkpoints.
The Electronic Brain talks to this gateway; no paid video API is involved.
"""
from __future__ import annotations

import os
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Electronic Brain - Wan2.1 Gateway", version="1.0")

WAN_DIR = Path(os.getenv("WAN_DIR", "/opt/Wan2.1")).resolve()
WAN_CKPT_DIR = os.getenv("WAN_CKPT_DIR", "").strip()
WAN_PYTHON = os.getenv("WAN_PYTHON", "python")
WAN_TASK = os.getenv("WAN_TASK", "t2v-1.3B")
WAN_SIZE = os.getenv("WAN_SIZE", "832*480")
WAN_OUTPUT_DIR = Path(os.getenv("WAN_OUTPUT_DIR", str(WAN_DIR / "outputs"))).resolve()
WAN_TOKEN = os.getenv("WAN_TOKEN", "").strip()

JOBS: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()


class GenerateRequest(BaseModel):
    prompt: str
    size: str | None = None
    task: str | None = None
    frame_num: int | None = None


def auth(token: str | None) -> None:
    if WAN_TOKEN and token != WAN_TOKEN:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")


def _run(job_id: str, req: GenerateRequest, output: Path) -> None:
    with LOCK:
        JOBS[job_id]["status"] = "RUNNING"
    cmd = [
        WAN_PYTHON,
        str(WAN_DIR / "generate.py"),
        "--task", req.task or WAN_TASK,
        "--size", req.size or WAN_SIZE,
        "--ckpt_dir", WAN_CKPT_DIR,
        "--prompt", req.prompt,
        "--save_file", str(output),
    ]
    if req.frame_num is not None:
        cmd += ["--frame_num", str(req.frame_num)]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(WAN_DIR),
            text=True,
            capture_output=True,
            timeout=int(os.getenv("WAN_JOB_TIMEOUT", "3600")),
            check=False,
        )
        with LOCK:
            JOBS[job_id].update({
                "status": "SUCCEEDED" if proc.returncode == 0 and output.exists() else "FAILED",
                "returncode": proc.returncode,
                "output": str(output) if output.exists() else None,
                "stderr": proc.stderr[-4000:],
            })
    except Exception as exc:
        with LOCK:
            JOBS[job_id].update({"status": "FAILED", "error": str(exc)})


@app.get("/health")
def health():
    return {
        "ok": True,
        "provider": "Wan2.1",
        "wan_dir_exists": WAN_DIR.is_dir(),
        "checkpoint_configured": bool(WAN_CKPT_DIR),
    }


@app.post("/generate")
def generate(req: GenerateRequest, authorization: str | None = Header(default=None)):
    auth(authorization.removeprefix("Bearer ").strip() if authorization else None)
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="PROMPT_REQUIRED")
    if not WAN_CKPT_DIR:
        raise HTTPException(status_code=503, detail="WAN_CKPT_DIR_NOT_CONFIGURED")
    WAN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    output = WAN_OUTPUT_DIR / f"{job_id}.mp4"
    with LOCK:
        JOBS[job_id] = {"id": job_id, "status": "QUEUED", "output": str(output)}
    threading.Thread(target=_run, args=(job_id, req, output), daemon=True).start()
    return {"ok": True, "job_id": job_id, "status": "QUEUED"}


@app.get("/jobs/{job_id}")
def job(job_id: str, authorization: str | None = Header(default=None)):
    auth(authorization.removeprefix("Bearer ").strip() if authorization else None)
    with LOCK:
        data = JOBS.get(job_id)
    if data is None:
        raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
    return data

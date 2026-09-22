""""RunPod Serverless worker for Wan2.1 T2V 1.3B."""
import os
import uuid
import subprocess
from pathlib import Path

import runpod

MODEL_ID = os.getenv("WAN_MODEL_ID", "Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
MODEL_DIR = os.getenv("WAN_MODEL_DIR", "/models/Wan2.1-T2V-1.3B-Diffusers")
OUTPUT_DIR = Path(os.getenv("WAN_OUTPUT_DIR", "/tmp/wan_outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def handler(job):
    inp = job.get("input", {})
    prompt = str(inp.get("prompt", "")).strip()
    if not prompt:
        return {"error": "prompt is required"}

    size = str(inp.get("size", "832*480"))
    out = OUTPUT_DIR / f"wan_{uuid.uuid4().hex}.mp4"
    cmd = [
        "python", "/opt/Wan2.1/generate.py",
        "--task", "t2v-1.3B",
        "--size", size,
        "--ckpt_dir", MODEL_DIR,
        "--prompt", prompt,
        "--save_file", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        return {"error": proc.stderr[-6000:]}
    return {"video_path": str(out), "prompt": prompt, "stdout": proc.stdout[-2000:]}


runpod.serverless.start({"handler": handler})
"
#!/usr/bin/env python3
"""Provider-neutral video generator adapter for Electronic Brain.

Set VIDEO_GENERATOR_COMMAND to a real video-generation command.
The command receives SCENE_JSON and OUTPUT_VIDEO through the environment.
FFmpeg normalization and verification remain the responsibility of the
cinematic factory.
"""
from __future__ import annotations
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

def generate(scene: dict, output_video: str) -> None:
    command = os.environ.get("VIDEO_GENERATOR_COMMAND", "").strip()
    if not command:
        raise RuntimeError("VIDEO_GENERATOR_NOT_CONNECTED")
    out = Path(output_video)
    out.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["SCENE_JSON"] = json.dumps(scene, ensure_ascii=False)
    env["OUTPUT_VIDEO"] = str(out)
    result = subprocess.run(shlex.split(command), env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"VIDEO_GENERATOR_FAILED: exit_code={result.returncode}")
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("VIDEO_GENERATOR_NO_OUTPUT")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: video_generator_adapter.py SCENE_JSON OUTPUT_VIDEO")
    scene = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    generate(scene, sys.argv[2])

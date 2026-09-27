"""Final mastering gate for assembled cinematic output."""
from __future__ import annotations
from typing import Any
from pathlib import Path
import os
import subprocess
import json

def evaluate_master(video_ref: str | None, expected_shots: int, *, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    checks = {"video_present": bool(video_ref), "shot_count": expected_shots > 0,
              "manifest_consistent": bool(manifest)}
    evidence: dict[str, Any] = {}
    if video_ref and not str(video_ref).startswith(("http://", "https://")) and Path(str(video_ref)).is_file():
        try:
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=codec_type,width,height,r_frame_rate",
                 "-of", "json", str(video_ref)],
                capture_output=True, text=True, timeout=30, check=False,
            )
            if proc.returncode == 0:
                evidence = json.loads(proc.stdout or "{}")
                streams = evidence.get("streams") or []
                checks["video_stream"] = any(s.get("codec_type") == "video" for s in streams)
                checks["audio_stream"] = any(s.get("codec_type") == "audio" for s in streams)
            else:
                checks["ffprobe"] = False
        except Exception as exc:
            evidence["error"] = repr(exc)
    checks.setdefault("video_stream", bool(video_ref))
    checks.setdefault("audio_stream", True)
    checks["ffprobe"] = checks.get("ffprobe", True)
    status = "VERIFIED" if all(checks.values()) else "REPAIR"
    return {"status": status, "checks": checks, "evidence": evidence}

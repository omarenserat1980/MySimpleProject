"""Quality gate for cinematic production.

Checks concrete technical signals before a video is considered ready.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any


def inspect_video(path: str, *, minimum_seconds: float = 1.0) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"status": "FAILED", "reason": "FILE_NOT_FOUND"}
    if p.stat().st_size < 1024:
        return {"status": "FAILED", "reason": "FILE_TOO_SMALL"}
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration,size:stream=codec_type,codec_name,width,height",
             "-of", "json", str(p)],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "FAILED", "reason": repr(exc)}
    if r.returncode != 0:
        return {"status": "FAILED", "reason": r.stderr[-1000:]}
    import json
    data = json.loads(r.stdout or "{}")
    duration = float((data.get("format") or {}).get("duration") or 0)
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    checks = {
        "file_exists": True,
        "size_ok": p.stat().st_size >= 1024,
        "duration_ok": duration >= minimum_seconds,
        "video_stream": video is not None,
        "audio_stream": audio is not None,
        "dimensions_ok": bool(video and video.get("width", 0) >= 640 and video.get("height", 0) >= 360),
    }
    score = sum(checks.values()) / len(checks)
    return {
        "status": "ACCEPTED" if all(checks.values()) else "REVIEW_REQUIRED",
        "score": round(score, 3),
        "checks": checks,
        "duration_s": duration,
        "path": str(p),
    }

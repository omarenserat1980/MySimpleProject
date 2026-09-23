"""Free local video renderer fallback.

Creates lightweight MP4 motion cards with FFmpeg. This is intentionally
CPU-friendly and does not require a paid video-generation API or GPU.
It is a real video-production fallback, not an AI text-to-video model.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _safe_text(value: str) -> str:
    value = re.sub(r"[^\w\s\-.,:!?()/]", " ", str(value), flags=re.UNICODE)
    return " ".join(value.split())[:140] or "Electronic Brain"


class LocalMotionRenderer:
    """Render a simple animated MP4 locally using FFmpeg."""

    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = Path(output_dir or os.getenv("LOCAL_MEDIA_DIR", "/tmp/brain_media"))
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        if not authorized:
            return {
                "status": "AUTHORIZATION_REQUIRED",
                "reason": "Local media production requires explicit production authorization.",
            }

        shot_id = str(shot.get("shot_id") or "shot")
        duration = max(2, min(30, int(float(shot.get("duration_s", 5) or 5))))
        title = _safe_text(
            shot.get("action")
            or shot.get("purpose")
            or shot.get("visual_prompt")
            or shot_id
        )
        filename = self.output_dir / f"{shot_id}.mp4"

        # Use FFmpeg's built-in lavfi source: no external media download required.
        # The zoom expression adds visible motion while keeping CPU requirements low.
        vf = (
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
            "zoompan=z='min(zoom+0.0008,1.08)':d=1:s=1280x720:fps=24,"
            "format=yuv420p"
        )
        draw = (
            "drawtext="
            "fontcolor=white:fontsize=42:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            f"text='{title.replace(chr(39), chr(92)+chr(39))}'"
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "color=c=black:s=1280x720:r=24",
            "-t", str(duration),
            "-vf", f"{vf},{draw}",
            "-an",
            "-c:v", "libx264",
            "-preset", os.getenv("LOCAL_FFMPEG_PRESET", "veryfast"),
            "-crf", "28",
            "-movflags", "+faststart",
            str(filename),
        ]

        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(60, duration * 20),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "RENDER_FAILED", "error": repr(exc)}

        if completed.returncode != 0 or not filename.exists():
            return {
                "status": "RENDER_FAILED",
                "error": completed.stderr[-2000:],
            }

        return {
            "status": "VERIFIED_COMPLETED",
            "shot_id": shot_id,
            "video_ref": str(filename),
            "duration_s": duration,
            "renderer": "local_ffmpeg_motion",
        }

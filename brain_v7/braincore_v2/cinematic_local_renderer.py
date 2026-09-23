"""Free CPU-friendly cinematic renderer.

This is not a text-to-video AI model. It creates stylized cinematic scenes from
FFmpeg primitives, with animated light, depth-like bands, film grain, vignette,
and generated ambient audio. Heavy AI rendering remains optional.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any


def _safe_text(value: str) -> str:
    value = re.sub(r"[^\w\s\-.,:!?()/]", " ", str(value), flags=re.UNICODE)
    return " ".join(value.split())[:180] or "Cinematic scene"


class CinematicLocalRenderer:
    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = Path(output_dir or os.getenv("LOCAL_MEDIA_DIR", "/tmp/brain_media"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = os.getenv("FFMPEG_BIN", "ffmpeg")

    def render(self, *, shot: dict[str, Any], authorized: bool = False) -> dict[str, Any]:
        if not authorized:
            return {"status": "AUTHORIZATION_REQUIRED"}

        shot_id = str(shot.get("shot_id") or "shot")
        duration = max(3, min(30, int(float(shot.get("duration_s", 5) or 5))))
        text = _safe_text(shot.get("action") or shot.get("purpose") or shot_id)
        out = self.output_dir / f"{shot_id}_cinematic.mp4"

        # One lavfi video source keeps the renderer portable and memory-light.
        # The animated radial light and lower foreground create a simple cinematic
        # depth cue without requiring downloaded images or a GPU.
        visual = (
            "color=c=0x0b1020:s=1280x720:r=24,"
            "geq="
            "r='12+22*Y/H+35*exp(-((X/W-(0.22+0.06*sin(T/3)))^2+(Y/H-0.28)^2)*18)':"
            "g='16+18*Y/H+22*exp(-((X/W-(0.22+0.06*sin(T/3)))^2+(Y/H-0.28)^2)*18)':"
            "b='34+28*Y/H+8*exp(-((X/W-(0.22+0.06*sin(T/3)))^2+(Y/H-0.28)^2)*18)',"
            "drawbox=x=0:y='H*0.70':w=W:h='H*0.30':color=black@0.72:t=fill,"
            "drawbox=x='W*(0.10+0.05*sin(T/4))':y='H*0.18':w='W*0.55':h='H*0.02':color=white@0.08:t=fill,"
            "noise=alls=4:allf=t+u,"
            # Autonomous camera movement: slow push-in plus horizontal/vertical drift.
            # Deterministic FFmpeg expressions keep this CPU-friendly and asset-free.
            "scale=1472:828:flags=lanczos,"
            "crop=1280:720:x=96+48*sin(T/4):y=54+27*cos(T/5),"
            "vignette=PI/4,"
            "format=yuv420p,"
            f"drawtext=fontcolor=white:fontsize=38:x=(w-text_w)/2:y=h-110:text='{text.replace(chr(39), chr(92)+chr(39))}'"
        )
        audio = (
            f"sine=frequency=110:sample_rate=48000,"
            f"afade=t=in:st=0:d=1,afade=t=out:st={max(1, duration-1)}:d=1,"
            "volume=0.10"
        )
        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi", "-i", visual,
            "-f", "lavfi", "-i", audio,
            "-t", str(duration),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264",
            "-preset", os.getenv("LOCAL_FFMPEG_PRESET", "veryfast"),
            "-crf", "27", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k",
            "-shortest", "-movflags", "+faststart", str(out),
        ]
        try:
            p = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=max(90, duration * 25), check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "RENDER_FAILED", "error": repr(exc)}
        if p.returncode != 0 or not out.is_file() or out.stat().st_size < 1024:
            return {"status": "RENDER_FAILED", "error": p.stderr[-3000:]}
        return {
            "status": "VERIFIED_COMPLETED",
            "shot_id": shot_id,
            "video_ref": str(out),
            "duration_s": duration,
            "renderer": "local_ffmpeg_cinematic",
        }

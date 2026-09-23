"""Free CPU-friendly cinematic renderer.

This is not a text-to-video AI model. It creates stylized cinematic scenes from
FFmpeg primitives, with motion, depth-like layers, vignette and generated sound.
It is designed for machines without a GPU and keeps the heavy AI stage optional.
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

        # Generated visual layers: gradient sky, moving light, silhouette-like foreground,
        # film grain and vignette. No external assets and no GPU are required.
        bg = (
            "color=c=0x111827:s=1280x720:r=24,"
            "format=yuv420p,"
            "geq="
            "r='18+22*Y/H+10*sin(2*PI*(X/W+T/8))':"
            "g='24+16*Y/H+8*sin(2*PI*(X/W+T/10))':"
            "b='40+28*Y/H+14*cos(2*PI*(X/W+T/12))'"
        )
        light = (
            "nullsrc=s=1280x720:r=24,"
            "geq="
            "r='150*exp(-((X-(W*(0.20+0.08*sin(T/4))) )^2+(Y-H*0.30)^2)/(2*220^2))':"
            "g='110*exp(-((X-(W*(0.20+0.08*sin(T/4))) )^2+(Y-H*0.30)^2)/(2*220^2))':"
            "b='55*exp(-((X-(W*(0.20+0.08*sin(T/4))) )^2+(Y-H*0.30)^2)/(2*220^2))',"
            "format=rgba"
        )
        # Keep the light layer subtle; screen blend creates a filmic glow.
        fg = (
            "color=c=0x050505:s=1280x720:r=24,"
            "drawbox=x=0:y=H*0.72:w=W:h=H*0.28:color=black@0.72:t=fill"
        )
        base = (
            f"[0:v][1:v]blend=all_mode=screen:all_opacity=0.55[tmp];"
            f"[tmp][2:v]blend=all_mode=overlay:all_opacity=0.55,"
            f"noise=alls=5:allf=t+u,"
            f"vignette=PI/4,"
            f"drawtext=fontcolor=white:fontsize=38:"
            f"x=(w-text_w)/2:y=h-110:"
            f"text='{text.replace(chr(39), chr(92)+chr(39))}'"
        )
        audio = (
            "sine=frequency=110:sample_rate=48000,"
            "afade=t=in:st=0:d=1,afade=t=out:st="
            f"{max(1, duration-1)}:d=1,volume=0.10"
        )
        filter_complex = f"{base};[3:a]{audio}"  # placeholder corrected below

        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi", "-i", bg,
            "-f", "lavfi", "-i", light,
            "-f", "lavfi", "-i", fg,
            "-f", "lavfi", "-i", audio,
            "-t", str(duration),
            "-filter_complex", base + ";[3:a]anull[a]",
            "-map", "[v]" if "[v]" in base else "0:v",
            "-map", "[a]",
            "-c:v", "libx264", "-preset", os.getenv("LOCAL_FFMPEG_PRESET", "veryfast"),
            "-crf", "27", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k",
            "-shortest", "-movflags", "+faststart", str(out),
        ]
        # The visual graph above ends without a label; normalize it by appending [v].
        cmd[cmd.index("-filter_complex") + 1] = base + "[v];[3:a]anull[a]"

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=max(90, duration * 25))
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

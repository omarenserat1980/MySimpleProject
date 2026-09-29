#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, subprocess, shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
OUT = ROOT / "brain_v12/web/media/engine/room-13-horror-10m-animatic.mp4"
PROGRESS = OUT.parent / "room-13-progress.json"
FONT = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
if not pathlib.Path(FONT).exists():
    FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

plan = json.loads(PLAN.read_text(encoding="utf-8"))
shots = plan["shots"]
target = float(plan["target_minutes"]) * 60
per = target / len(shots)
ff = shutil.which("ffmpeg")
if not ff:
    raise SystemExit("FFMPEG_NOT_INSTALLED")

OUT.parent.mkdir(parents=True, exist_ok=True)
segments = []

def esc(t: str) -> str:
    return (str(t).replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "\\'").replace("%", "\\%").replace(",", "\\,"))

def write_progress(status: str, percent: int, shot: int = 0) -> None:
    PROGRESS.write_text(json.dumps({
        "status": status, "percent": percent, "shot": shot,
        "total_shots": len(shots), "duration_seconds": target,
        "output": str(OUT)
    }, ensure_ascii=False, indent=2), encoding="utf-8")

write_progress("STARTED", 0, 0)

for i, s in enumerate(shots):
    d = per
    progress = int(((i + 1) / len(shots)) * 100)
    label = esc(f'{s["id"]} — {s["visual"]}')
    vf = (
        f"scale=1920:1080,format=yuv420p,"
        f"drawtext=fontfile='{FONT}':text='{label}':x=(w-text_w)/2:"
        f"y=(h-text_h)/2:fontsize=42:fontcolor=white:borderw=3:bordercolor=black,"
        f"fade=t=in:st=0:d=1,fade=t=out:st={max(0, d-1)}:d=1"
    )
    out = OUT.parent / f"room13-segment-{i:02d}.mp4"
    freq = 90 + (i % 12) * 11
    subprocess.run([
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=1920x1080:r=24",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=48000",
        "-t", f"{d:.3f}", "-vf", vf,
        "-af", "volume=0.035,afade=t=in:st=0:d=1,afade=t=out:st=17.75:d=1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "96k", "-ar", "48000", "-ac", "2",
        "-pix_fmt", "yuv420p", str(out)
    ], check=True)
    segments.append(out)
    write_progress("RENDERING", progress, i + 1)
    print(f"ROOM_13_PROGRESS={progress}% shot={i+1}/{len(shots)}", flush=True)

lst = OUT.parent / "room13-concat.txt"
lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
subprocess.run([
    ff, "-y", "-hide_banner", "-loglevel", "error",
    "-f", "concat", "-safe", "0", "-i", str(lst),
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
    "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)
], check=True)

for pth in segments:
    pth.unlink(missing_ok=True)
lst.unlink(missing_ok=True)
# Final integrity checks before declaring the render complete.
if not OUT.exists() or OUT.stat().st_size < 1024:
    write_progress("FAILED", 100, len(shots))
    raise SystemExit("ROOM13_OUTPUT_INVALID")
probe = subprocess.run([
    ff, "-v", "error", "-show_entries",
    "format=duration,size:stream=codec_type,codec_name,width,height",
    "-of", "json", str(OUT)
], capture_output=True, text=True, check=True)
meta = json.loads(probe.stdout)
duration = float(meta.get("format", {}).get("duration", 0))
streams = meta.get("streams", [])
has_video = any(x.get("codec_type") == "video" and x.get("width") == 1920 and x.get("height") == 1080 for x in streams)
has_audio = any(x.get("codec_type") == "audio" and x.get("codec_name") == "aac" for x in streams)
if duration < target - 2 or not has_video or not has_audio:
    write_progress("FAILED_QC", 100, len(shots))
    raise SystemExit(f"ROOM13_QC_FAILED duration={duration} video={has_video} audio={has_audio}")

write_progress("RENDERED", 100, len(shots))
print(json.dumps({
    "status": "RENDERED", "percent": 100, "output": str(OUT),
    "duration_seconds": target, "shots": len(shots), "audio": True
}, ensure_ascii=False))

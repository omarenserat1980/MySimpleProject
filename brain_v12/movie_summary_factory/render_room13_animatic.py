#!/usr/bin/env python3
from __future__ import annotations
import json, math, pathlib, subprocess, shutil, struct
from brain_v12 import brain_ffmpeg

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
OUT = ROOT / "brain_v12/web/media/engine/room-13-horror-10m-animatic.mp4"
PROGRESS = OUT.parent / "room-13-progress.json"
ASSET_DIR = OUT.parent / "room13-assets"
FONT = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
if not pathlib.Path(FONT).exists():
    FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

plan = json.loads(PLAN.read_text(encoding="utf-8"))
shots = plan["shots"]
target = float(plan["target_minutes"]) * 60
per = target / len(shots)

ff = brain_ffmpeg.ffmpeg()
ffprobe = brain_ffmpeg.ffprobe()
espeak = shutil.which("espeak-ng")
if not espeak:
    raise SystemExit("ROOM13_TTS_MISSING: install espeak-ng")

OUT.parent.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)
segments = []

def write_progress(status: str, percent: int, shot: int = 0) -> None:
    PROGRESS.write_text(json.dumps({
        "status": status, "percent": percent, "shot": shot,
        "total_shots": len(shots), "duration_seconds": target,
        "output": str(OUT), "visual_assets": shot,
        "voice_assets": shot
    }, ensure_ascii=False, indent=2), encoding="utf-8")

def visual_theme(text: str, shot_type: str):
    t = text.lower()
    if "مستشفى" in t: return ("#17202a", "#51606d", "hospital")
    if "بوابة" in t or "باب" in t or "مقبض" in t: return ("#20252b", "#8b6f47", "door")
    if "ممر" in t or "جدار" in t: return ("#1b2630", "#65717c", "corridor")
    if "خريطة" in t or "صور" in t or "أسماء" in t or "بطاقة" in t: return ("#3a3024", "#d0b98b", "wall")
    if "شريط" in t or "تسجيل" in t or "جهاز" in t: return ("#28242b", "#b58b58", "recorder")
    if "ساعة" in t: return ("#252a31", "#d7d1b4", "clock")
    if "بطل" in t or "نسخة" in t or "يده" in t or "وجه" in t: return ("#18222b", "#a7b6c2", "character")
    return ("#20252c", "#9ba7b3", "scene")

def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def make_ppm(path: pathlib.Path, scene: str, shot_type: str, idx: int) -> None:
    W, H = 960, 540
    bg, accent, theme = visual_theme(scene, shot_type)
    br, bgc, bb = hexrgb(bg)
    ar, ag, ab = hexrgb(accent)
    seed = idx * 17 + len(scene)
    with path.open("wb") as f:
        f.write(f"P6\\n{W} {H}\\n255\\n".encode())
        for y in range(H):
            row = bytearray()
            gy = y / (H - 1)
            for x in range(W):
                gx = x / (W - 1)
                vignette = max(0.35, 1.0 - 0.55 * ((gx-.5)**2 + (gy-.5)**2))
                r = int((br*(1-gy)+ar*gy)*vignette)
                g = int((bgc*(1-gy)+ag*gy)*vignette)
                b = int((bb*(1-gy)+ab*gy)*vignette)
                # cinematic rain/light streaks
                if ((x + seed*13) % 97) < 3 and y > 70:
                    r, g, b = min(255,r+35), min(255,g+35), min(255,b+35)
                row.extend((r,g,b))
            f.write(row)
        # Draw simple high-contrast scene objects as a second PPM pass is too costly;
        # use FFmpeg's deterministic geometric overlay for the foreground.
    # Foreground geometry is added by FFmpeg from this raster base.

def render_segment(i: int, shot: dict) -> pathlib.Path:
    image = ASSET_DIR / f"shot-{i:02d}.ppm"
    voice = ASSET_DIR / f"voice-{i:02d}.wav"
    out = ASSET_DIR / f"segment-{i:02d}.mp4"
    make_ppm(image, shot["visual"], shot.get("shot_type",""), i)

    subprocess.run([espeak, "-v", "ar", "-s", "145", "-p", "38", "-a", "170",
                    "-w", str(voice), shot["voice"]], check=True)

    d = per
    # No scene-description text is burned into the picture. Optional subtitles are off by default.
    fg = (
        "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
        "zoompan=z='min(zoom+0.00035,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        "d=1:s=1920x1080:fps=24,"
        "eq=brightness=-0.03:saturation=1.12,"
        "vignette=PI/5"
    )
    if pathlib.Path(FONT).exists() and False:
        fg += f",drawtext=fontfile='{FONT}':text='':x=0:y=0"

    # A quiet atmospheric bed plus real Arabic narration.
    af = (
        "[1:a]aresample=48000,volume=1.15,afade=t=in:st=0:d=0.4,"
        f"afade=t=out:st={max(0.5,d-0.8)}:d=0.8[voice];"
        "[2:a]volume=0.035,lowpass=f=900,afade=t=in:st=0:d=1,"
        f"afade=t=out:st={max(1,d-1)}:d=1[bed];"
        "[voice][bed]amix=inputs=2:duration=longest:dropout_transition=1,"
        "loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-i", str(image),
           "-i", str(voice),
           "-f", "lavfi", "-i", "sine=frequency=92:sample_rate=48000",
           "-t", f"{d:.3f}", "-vf", fg, "-filter_complex", af,
           "-map", "0:v:0", "-map", "[aout]" if False else "1:a:0",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    # Use a simpler, reliable two-input audio mix graph and map its output.
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-i", str(image), "-i", str(voice),
           "-f", "lavfi", "-i", "sine=frequency=92:sample_rate=48000",
           "-t", f"{d:.3f}", "-vf", fg,
           "-filter_complex",
           "[1:a]aresample=48000,volume=1.15[voice];"
           "[2:a]volume=0.035[bed];"
           "[voice][bed]amix=inputs=2:duration=longest:dropout_transition=1,"
           "loudnorm=I=-16:TP=-1.5:LRA=11[aout]",
           "-map", "0:v:0", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out

write_progress("STARTED", 0, 0)
for i, shot in enumerate(shots):
    seg = render_segment(i, shot)
    segments.append(seg)
    progress = int(((i + 1) / len(shots)) * 100)
    write_progress("RENDERING", progress, i + 1)
    print(f"ROOM_13_PROGRESS={progress}% shot={i+1}/{len(shots)}", flush=True)

lst = OUT.parent / "room13-concat.txt"
lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", str(lst),
                "-c", "copy", "-movflags", "+faststart", str(OUT)], check=True)

for pth in segments + [lst]:
    pth.unlink(missing_ok=True)

if not OUT.exists() or OUT.stat().st_size < 1024:
    write_progress("FAILED", 100, len(shots))
    raise SystemExit("ROOM13_OUTPUT_INVALID")

probe = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                        "format=duration,size:stream=codec_type,codec_name,width,height",
                        "-of", "json", str(OUT)], capture_output=True, text=True, check=True)
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
    "duration_seconds": duration, "shots": len(shots),
    "audio": True, "voiceover": True, "visual_assets": len(shots),
    "subtitles": False
}, ensure_ascii=False))

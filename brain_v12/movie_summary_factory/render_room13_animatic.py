#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import pathlib
import shutil
import subprocess

from brain_v12 import brain_ffmpeg

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = pathlib.Path(os.getenv("BRAIN_CINEMATIC_PLAN", str(ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json")))
OUT = ROOT / "brain_v12/web/media/engine/room-13-horror-10m-animatic.mp4"
PROGRESS = OUT.parent / "room-13-progress.json"
ASSET_DIR = OUT.parent / "room13-assets"

plan = json.loads(PLAN.read_text(encoding="utf-8"))
shots = plan["shots"]
target = float(plan["target_minutes"]) * 60.0
per = target / max(1, len(shots))

ff = brain_ffmpeg.ffmpeg()
ffprobe = brain_ffmpeg.ffprobe()
espeak = shutil.which("espeak-ng")
if not espeak:
    raise SystemExit("ROOM13_TTS_MISSING: install espeak-ng")

OUT.parent.mkdir(parents=True, exist_ok=True)
ASSET_DIR.mkdir(parents=True, exist_ok=True)
segments: list[pathlib.Path] = []


def write_progress(status: str, percent: int, shot: int = 0) -> None:
    PROGRESS.write_text(
        json.dumps(
            {
                "status": status,
                "percent": percent,
                "shot": shot,
                "total_shots": len(shots),
                "duration_seconds": target,
                "output": str(OUT),
                "visual_assets": shot,
                "voice_assets": shot,
                "subtitles": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def theme_for(text: str) -> tuple[str, str, str]:
    t = text.lower()
    if "مستشفى" in t:
        return "#111923", "#9fb3c8", "hospital"
    if any(x in t for x in ("بوابة", "باب", "مقبض")):
        return "#15191e", "#b18a55", "door"
    if any(x in t for x in ("ممر", "جدار")):
        return "#101820", "#71808b", "corridor"
    if any(x in t for x in ("خريطة", "صور", "أسماء", "بطاقة")):
        return "#211d18", "#d0b98b", "wall"
    if any(x in t for x in ("شريط", "تسجيل", "جهاز")):
        return "#17171c", "#b98a55", "recorder"
    if "ساعة" in t:
        return "#14181d", "#d8d0b1", "clock"
    if any(x in t for x in ("بطل", "نسخة", "يده", "وجه")):
        return "#101923", "#a9bac8", "character"
    return "#111820", "#8fa1ad", "scene"


def blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(a[i] * (1.0 - t) + b[i] * t))) for i in range(3))


def rect(px: bytearray, w: int, h: int, x0: int, y0: int, x1: int, y1: int,
         color: tuple[int, int, int]) -> None:
    x0, x1 = max(0, min(x0, x1)), min(w - 1, max(x0, x1))
    y0, y1 = max(0, min(y0, y1)), min(h - 1, max(y0, y1))
    for y in range(y0, y1 + 1):
        base = y * w * 3
        for x in range(x0, x1 + 1):
            p = base + x * 3
            px[p:p + 3] = bytes(color)


def line(px: bytearray, w: int, h: int, x0: int, y0: int, x1: int, y1: int,
         color: tuple[int, int, int], thickness: int = 2) -> None:
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    for i in range(steps + 1):
        x = int(x0 + dx * i / steps)
        y = int(y0 + dy * i / steps)
        rect(px, w, h, x - thickness, y - thickness, x + thickness, y + thickness, color)


def circle(px: bytearray, w: int, h: int, cx: int, cy: int, r: int,
           color: tuple[int, int, int], fill: bool = True) -> None:
    rr = r * r
    for y in range(max(0, cy - r), min(h, cy + r + 1)):
        for x in range(max(0, cx - r), min(w, cx + r + 1)):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if (d <= rr if fill else rr - 4 * r <= d <= rr):
                p = (y * w + x) * 3
                px[p:p + 3] = bytes(color)


def polygon(px: bytearray, w: int, h: int, points: list[tuple[int, int]],
            color: tuple[int, int, int]) -> None:
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(h, max(ys) + 1)):
        xs = []
        for i, (x1, y1) in enumerate(points):
            x2, y2 = points[(i + 1) % len(points)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                x = int(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
                xs.append(x)
        xs.sort()
        for a, b in zip(xs[::2], xs[1::2]):
            rect(px, w, h, a, y, b, y, color)


def make_ppm(path: pathlib.Path, scene: str, shot_type: str, idx: int) -> None:
    # Deterministic illustrated keyframe: background + recognizable foreground object.
    w, h = 960, 540
    bg_hex, accent_hex, theme = theme_for(scene)
    bg, accent = rgb(bg_hex), rgb(accent_hex)
    px = bytearray(w * h * 3)

    for y in range(h):
        t = y / (h - 1)
        c = blend(bg, accent, t * 0.32)
        for x in range(w):
            v = max(0.38, 1.0 - 0.48 * (((x / w) - 0.5) ** 2 + ((y / h) - 0.5) ** 2))
            p = (y * w + x) * 3
            px[p:p + 3] = bytes(max(0, min(255, int(q * v))) for q in c)

    shadow = (8, 10, 12)
    light = tuple(min(255, q + 35) for q in accent)
    metal = (105, 116, 123)

    # Floor / perspective guides make the scene read as a physical space.
    polygon(px, w, h, [(0, 390), (w, 360), (w, h), (0, h)], (18, 21, 24))
    for i in range(9):
        yy = 390 + i * 18
        line(px, w, h, 0, yy, w, yy + 12, (38, 43, 47), 1)

    if theme == "hospital":
        rect(px, w, h, 95, 105, 865, 390, (38, 45, 52))
        rect(px, w, h, 120, 135, 330, 300, (18, 23, 27))
        rect(px, w, h, 365, 135, 575, 300, (22, 28, 32))
        rect(px, w, h, 610, 135, 840, 300, (17, 22, 26))
        rect(px, w, h, 165, 320, 720, 355, (92, 96, 96))
        rect(px, w, h, 235, 275, 650, 332, (145, 149, 148))
        rect(px, w, h, 270, 245, 615, 290, (178, 181, 176))
        rect(px, w, h, 270, 230, 615, 248, light)
        circle(px, w, h, 205, 160, 17, light)
        line(px, w, h, 205, 177, 205, 225, metal, 5)
    elif theme == "door":
        rect(px, w, h, 280, 55, 680, 430, (47, 43, 39))
        rect(px, w, h, 320, 75, 640, 430, (82, 60, 43))
        rect(px, w, h, 350, 105, 610, 400, (58, 45, 36))
        rect(px, w, h, 555, 245, 580, 280, light)
        circle(px, w, h, 575, 262, 10, metal)
        polygon(px, w, h, [(280, 55), (680, 55), (750, 105), (210, 105)], (75, 82, 86))
        rect(px, w, h, 70, 390, 890, 425, shadow)
    elif theme == "corridor":
        polygon(px, w, h, [(90, 80), (870, 80), (650, 390), (310, 390)], (42, 48, 53))
        polygon(px, w, h, [(0, 0), (960, 0), (870, 80), (90, 80)], (25, 31, 36))
        polygon(px, w, h, [(90, 80), (310, 390), (0, 540), (0, 0)], (28, 34, 39))
        polygon(px, w, h, [(870, 80), (960, 0), (960, 540), (650, 390)], (24, 30, 35))
        for x in (190, 770):
            rect(px, w, h, x, 120, x + 55, 365, (57, 63, 67))
            rect(px, w, h, x + 9, 140, x + 46, 350, (22, 27, 31))
        for x in (250, 710):
            rect(px, w, h, x, 95, x + 55, 110, light)
    elif theme == "wall":
        rect(px, w, h, 85, 70, 875, 390, (74, 63, 49))
        for x, y in ((135, 110), (360, 100), (600, 125), (205, 250), (490, 235), (720, 250)):
            rect(px, w, h, x, y, x + 125, y + 95, (20, 22, 22))
            rect(px, w, h, x + 7, y + 7, x + 118, y + 88, light)
            line(px, w, h, x + 20, y + 70, x + 105, y + 25, (45, 51, 55), 2)
    elif theme == "recorder":
        rect(px, w, h, 150, 300, 810, 400, (30, 31, 33))
        rect(px, w, h, 255, 205, 705, 345, (65, 68, 70))
        rect(px, w, h, 285, 230, 675, 305, (16, 19, 21))
        for x in (325, 400, 475, 550, 625):
            circle(px, w, h, x, 267, 18, metal)
            circle(px, w, h, x, 267, 7, light)
        rect(px, w, h, 350, 120, 610, 190, (22, 24, 26))
        line(px, w, h, 365, 155, 595, 155, light, 3)
    elif theme == "clock":
        circle(px, w, h, 480, 230, 150, (32, 35, 37))
        circle(px, w, h, 480, 230, 130, (174, 169, 145))
        circle(px, w, h, 480, 230, 122, (30, 33, 35))
        for a in range(0, 360, 30):
            rad = math.radians(a)
            x1, y1 = 480 + int(math.cos(rad) * 108), 230 + int(math.sin(rad) * 108)
            x2, y2 = 480 + int(math.cos(rad) * 122), 230 + int(math.sin(rad) * 122)
            line(px, w, h, x1, y1, x2, y2, light, 4)
        line(px, w, h, 480, 230, 430, 170, light, 7)
        line(px, w, h, 480, 230, 535, 250, light, 5)
        circle(px, w, h, 480, 230, 9, light)
    elif theme == "character":
        # Human silhouette, clearly visible against the background.
        circle(px, w, h, 480, 155, 58, (164, 144, 128))
        rect(px, w, h, 430, 210, 530, 270, (116, 91, 76))
        polygon(px, w, h, [(355, 500), (395, 270), (565, 270), (605, 500)], (35, 43, 49))
        polygon(px, w, h, [(405, 290), (300, 405), (330, 425), (455, 330)], (44, 54, 61))
        polygon(px, w, h, [(555, 290), (660, 405), (630, 425), (505, 330)], (44, 54, 61))
        circle(px, w, h, 460, 150, 6, shadow)
        circle(px, w, h, 500, 150, 6, shadow)
        line(px, w, h, 455, 178, 505, 178, shadow, 3)
    else:
        rect(px, w, h, 125, 95, 835, 355, (39, 47, 52))
        rect(px, w, h, 175, 135, 420, 310, (19, 25, 29))
        rect(px, w, h, 500, 135, 785, 310, (22, 28, 32))
        circle(px, w, h, 480, 220, 45, light)
        line(px, w, h, 480, 220, 510, 190, shadow, 5)

    # A restrained moving-light motif; no text is rendered into the artwork.
    seed = idx * 37 + len(scene) * 11
    for n in range(5):
        x = 60 + ((seed + n * 173) % 820)
        line(px, w, h, x, 70, x - 55, 390, (65, 72, 78), 1)

    with path.open("wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
        f.write(px)


def render_segment(i: int, shot: dict) -> pathlib.Path:
    image = ASSET_DIR / f"shot-{i:02d}.ppm"
    voice = ASSET_DIR / f"voice-{i:02d}.wav"
    out = ASSET_DIR / f"segment-{i:02d}.mp4"

    make_ppm(image, shot["visual"], shot.get("shot_type", ""), i)

    subprocess.run(
        [
            espeak, "-v", "ar", "-s", "145", "-p", "38", "-a", "170",
            "-w", str(voice), shot["voice"],
        ],
        check=True,
    )

    d = per
    vf = (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,"
        "zoompan=z='min(zoom+0.00030,1.08)':"
        "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        "d=1:s=1920x1080:fps=24,"
        "eq=brightness=-0.015:saturation=1.08,"
        "vignette=PI/5"
    )
    audio = (
        "[1:a]aresample=48000,highpass=f=70,volume=1.20,"
        "afade=t=in:st=0:d=0.35,"
        f"afade=t=out:st={max(0.5, d - 0.8):.3f}:d=0.8[voice];"
        "[2:a]volume=0.018,lowpass=f=900,"
        f"afade=t=out:st={max(0.5, d - 1.0):.3f}:d=1[bed];"
        "[voice][bed]amix=inputs=2:duration=longest:dropout_transition=1,"
        "loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    )
    cmd = [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", str(image),
        "-i", str(voice),
        "-f", "lavfi", "-i", "sine=frequency=92:sample_rate=48000",
        "-t", f"{d:.3f}", "-vf", vf,
        "-filter_complex", audio,
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


write_progress("STARTED", 0, 0)
for i, shot in enumerate(shots):
    seg = render_segment(i, shot)
    segments.append(seg)
    progress = int(((i + 1) / len(shots)) * 100)
    write_progress("RENDERING", progress, i + 1)
    print(f"ROOM_13_PROGRESS={progress}% shot={i + 1}/{len(shots)}", flush=True)

lst = OUT.parent / "room13-concat.txt"
lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
subprocess.run(
    [
        ff, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lst),
        "-c", "copy", "-movflags", "+faststart", str(OUT),
    ],
    check=True,
)

for pth in segments + [lst]:
    pth.unlink(missing_ok=True)

if not OUT.exists() or OUT.stat().st_size < 1024:
    write_progress("FAILED", 100, len(shots))
    raise SystemExit("ROOM13_OUTPUT_INVALID")

probe = subprocess.run(
    [
        ffprobe, "-v", "error", "-show_entries",
        "format=duration,size:stream=codec_type,codec_name,width,height",
        "-of", "json", str(OUT),
    ],
    capture_output=True, text=True, check=True,
)
meta = json.loads(probe.stdout)
duration = float(meta.get("format", {}).get("duration", 0))
streams = meta.get("streams", [])
has_video = any(
    s.get("codec_type") == "video" and s.get("width") == 1920 and s.get("height") == 1080
    for s in streams
)
has_audio = any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac" for s in streams)

if duration < target - 2 or not has_video or not has_audio:
    write_progress("FAILED_QC", 100, len(shots))
    raise SystemExit(
        f"ROOM13_QC_FAILED duration={duration} video={has_video} audio={has_audio}"
    )

write_progress("RENDERED", 100, len(shots))
print(
    json.dumps(
        {
            "status": "RENDERED",
            "percent": 100,
            "output": str(OUT),
            "duration_seconds": duration,
            "shots": len(shots),
            "audio": True,
            "voiceover": True,
            "visual_assets": len(shots),
            "subtitles": False,
        },
        ensure_ascii=False,
    )
)

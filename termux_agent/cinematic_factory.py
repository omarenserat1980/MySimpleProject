#!/usr/bin/env python3
"""PHONE-ONLY cinematic factory for Electronic Brain.

The factory is deliberately provider-agnostic:
- a local VIDEO_RENDER_COMMAND may generate each 30s scene;
- FFmpeg/ffprobe normalizes and verifies every part;
- state is persisted so verified parts are never regenerated;
- an optional PUBLISH_COMMAND can hand a verified MP4 to a phone publishing app.

No credentials are stored in this file.
"""
from __future__ import annotations
import json, os, shlex, subprocess, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(os.getenv("CINEMATIC_FACTORY_ROOT", Path.cwd())).resolve()
STATE = ROOT / os.getenv("CINEMATIC_STATE", "cinematic_factory_state.json")
MANIFEST = ROOT / os.getenv("CINEMATIC_MANIFEST", "cinematic_film_manifest.json")
OUT = ROOT / os.getenv("CINEMATIC_OUTPUT_DIR", "cinematic_output")
RENDER_CMD = os.getenv("VIDEO_RENDER_COMMAND", "").strip()
IMAGE_AUDIO_ROOT = ROOT / os.getenv("IMAGE_AUDIO_ROOT", "cinematic_assets")
PUBLISH_CMD = os.getenv("PUBLISH_COMMAND", "").strip()

def run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)

def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def verify(path: Path, expected_seconds: float = 30.0) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size < 1024:
        return {"ok": False, "reason": "FILE_MISSING_OR_TOO_SMALL"}
    p = run(["ffprobe","-v","error","-show_entries",
             "format=duration,size:stream=codec_type,codec_name,width,height",
             "-of","json",str(path)], 60)
    if p.returncode:
        return {"ok": False, "reason": p.stderr[-1000:]}
    data=json.loads(p.stdout or "{}")
    duration=float((data.get("format") or {}).get("duration") or 0)
    streams=data.get("streams") or []
    video=next((s for s in streams if s.get("codec_type")=="video"), None)
    audio=next((s for s in streams if s.get("codec_type")=="audio"), None)
    checks={
        "duration_30s": abs(duration-expected_seconds) <= 0.10,
        "video": video is not None,
        "audio": audio is not None,
        "hd": bool(video and video.get("width",0)>=1280 and video.get("height",0)>=720),
    }
    return {"ok": all(checks.values()), "duration_s": duration,
            "checks": checks, "codec_video": (video or {}).get("codec_name"),
            "codec_audio": (audio or {}).get("codec_name")}

def normalize(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Force exactly 30s and a broadly compatible YouTube format.
    cmd=["ffmpeg","-y","-i",str(src),"-t","30",
         "-vf","scale=1920:1080:force_original_aspect_ratio=decrease,"
               "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
         "-r","30","-c:v","libx264","-pix_fmt","yuv420p",
         "-c:a","aac","-ar","48000","-b:a","192k",str(dst)]
    p=run(cmd, 900)
    if p.returncode:
        raise RuntimeError(p.stderr[-2000:])

def render_image_audio_scene(part: dict[str, Any], raw: Path) -> None:
    """Build a 30s scene from still images plus audio using FFmpeg only."""
    key = f"{int(part['part']):02d}"
    asset_dir = (IMAGE_AUDIO_ROOT / key).resolve()
    if not asset_dir.is_dir():
        raise RuntimeError(f"IMAGE_AUDIO_ASSETS_MISSING: part={key}")
    images = sorted(p for p in asset_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    audio = sorted(p for p in asset_dir.iterdir() if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".ogg"})
    if not images or not audio:
        raise RuntimeError(f"IMAGE_AUDIO_ASSETS_MISSING: part={key} images={len(images)} audio={len(audio)}")
    raw.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=raw.parent, prefix=f"ia_{key}_") as td:
        td = Path(td)
        if len(images) == 1:
            vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
                  "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                  "zoompan=z='min(zoom+0.0008,1.12)':d=900:s=1920x1080:fps=30")
            cmd = ["ffmpeg","-y","-loop","1","-i",str(images[0]),"-i",str(audio[0]),"-t","30",
                   "-vf",vf,"-r","30","-c:v","libx264","-pix_fmt","yuv420p",
                   "-c:a","aac","-ar","48000","-b:a","192k","-shortest",str(raw)]
        else:
            duration = 30.0 / len(images)
            concat = td / "images.txt"
            lines = []
            for img in images:
                lines.extend([f"file '{img.as_posix()}'", f"duration {duration:.6f}"])
            lines.append(f"file '{images[-1].as_posix()}'")
            concat.write_text("\n".join(lines), encoding="utf-8")
            cmd = ["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-i",str(audio[0]),"-t","30",
                   "-vf","scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30",
                   "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-b:a","192k","-shortest",str(raw)]
        p = run(cmd, 900)
        if p.returncode:
            raise RuntimeError(p.stderr[-3000:])

def render_scene(part: dict[str, Any], raw: Path) -> None:
    if os.getenv("IMAGE_AUDIO_MODE","1").lower() in {"1","true","yes","on"}:
        try:
            render_image_audio_scene(part, raw)
            return
        except RuntimeError as exc:
            if "IMAGE_AUDIO_ASSETS_MISSING" not in str(exc):
                raise
    source=part.get("source")
    if source:
        src=(ROOT / source).resolve()
        if not src.is_file():
            raise FileNotFoundError(f"source not found: {src}")
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(src.read_bytes())
        return
    if not RENDER_CMD:
        raise RuntimeError("IMAGE_AUDIO_ASSETS_MISSING and VIDEO_RENDER_COMMAND is not configured")
    env=os.environ.copy()
    env["SCENE_JSON"]=json.dumps(part, ensure_ascii=False)
    env["OUTPUT_VIDEO"]=str(raw)
    p=subprocess.run(shlex.split(RENDER_CMD), env=env, capture_output=True,
                    text=True, timeout=1800, check=False)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-3000:])

def publish(part: dict[str, Any], video: Path) -> dict[str, Any]:
    if not PUBLISH_CMD:
        return {"ok": False, "status": "PUBLISH_COMMAND_NOT_CONFIGURED"}
    env=os.environ.copy()
    env["VIDEO_FILE"]=str(video)
    env["PART_NUMBER"]=str(part["part"])
    env["VIDEO_TITLE"]=str(part["title"])
    env["VIDEO_DESCRIPTION"]=str(part.get("description",""))
    p=subprocess.run(shlex.split(PUBLISH_CMD), env=env, capture_output=True,
                    text=True, timeout=1800, check=False)
    return {"ok": p.returncode==0, "status": "PUBLISHED" if p.returncode==0 else "PUBLISH_FAILED",
            "stdout":p.stdout[-2000:], "stderr":p.stderr[-2000:]}

def main() -> int:
    manifest=load_json(MANIFEST, {})
    parts=manifest.get("parts", [])
    if len(parts)!=60:
        raise SystemExit(f"manifest must contain exactly 60 parts; got {len(parts)}")
    OUT.mkdir(parents=True, exist_ok=True)
    state=load_json(STATE, {"film_id":manifest.get("film_id"),"parts":{}})
    for expected, part in enumerate(parts, 1):
        if int(part.get("part",0)) != expected:
            raise SystemExit(f"part numbering error at index {expected}")
        key=f"{expected:02d}"
        rec=state["parts"].get(key, {})
        final=OUT / f"part_{key}.mp4"
        if rec.get("verified") and final.is_file() and verify(final)["ok"]:
            if rec.get("published"):
                continue
        try:
            if not rec.get("verified"):
                with tempfile.TemporaryDirectory(dir=OUT, prefix=f"factory_{key}_") as td:
                    raw=Path(td)/"raw.mp4"
                    render_scene(part, raw)
                    normalize(raw, final)
                check=verify(final)
                if not check["ok"]:
                    raise RuntimeError(f"QUALITY_GATE_FAILED: {check}")
                rec.update({"verified":True,"verification":check})
                state["parts"][key]=rec
                save_json(STATE,state)
            if not rec.get("published"):
                pub=publish(part, final)
                rec.update({"published":bool(pub.get("ok")),"publication":pub})
                state["parts"][key]=rec
                save_json(STATE,state)
                if not pub.get("ok"):
                    print(json.dumps({"part":expected,"status":"VERIFIED_NOT_PUBLISHED","detail":pub},ensure_ascii=False))
                    return 2
            print(json.dumps({"part":expected,"status":"PUBLISHED"},ensure_ascii=False))
        except Exception as exc:
            rec.update({"verified":False,"error":str(exc)})
            state["parts"][key]=rec
            save_json(STATE,state)
            print(json.dumps({"part":expected,"status":"FAILED","error":str(exc)},ensure_ascii=False))
            return 1
    state["status"]="COMPLETE"
    save_json(STATE,state)
    print(json.dumps({"status":"COMPLETE","parts":60,"runtime_seconds":1800},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())

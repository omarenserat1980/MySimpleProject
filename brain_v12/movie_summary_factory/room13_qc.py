#!/usr/bin/env python3
"""Reusable Room 13 production QC for Brain Cloud and GitHub Actions."""
from __future__ import annotations
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
OUT = ROOT / "brain_v12/web/media/engine/room-13-horror-10m-animatic.mp4"
REPORT = OUT.parent / "room-13-qc.json"

def fail(errors, warnings=None):
    report = {
        "status": "FAILED",
        "errors": errors,
        "warnings": warnings or [],
        "plan": str(PLAN),
        "output": str(OUT),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(1)

def main():
    errors, warnings = [], []
    if not PLAN.exists():
        fail(["PLAN_NOT_FOUND"])
    try:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
    except Exception as exc:
        fail([f"PLAN_JSON_INVALID:{exc}"])

    beats = plan.get("beats", [])
    shots = plan.get("shots", [])
    target = float(plan.get("target_minutes", 0)) * 60
    if len(beats) != 8: errors.append(f"EXPECTED_8_BEATS:{len(beats)}")
    if len(shots) != 32: errors.append(f"EXPECTED_32_SHOTS:{len(shots)}")
    if target <= 0: errors.append("TARGET_DURATION_INVALID")

    ids = set()
    for shot in shots:
        sid = shot.get("id")
        if not sid or sid in ids: errors.append(f"DUPLICATE_OR_MISSING_SHOT_ID:{sid}")
        ids.add(sid)
        for key in ("visual", "voice", "subtitle", "transition", "camera"):
            if not shot.get(key): errors.append(f"MISSING_{key.upper()}:{sid}")
        if float(shot.get("duration_s", 0)) <= 0: errors.append(f"INVALID_DURATION:{sid}")

    ff = shutil.which("ffmpeg")
    fp = shutil.which("ffprobe")
    if not ff: errors.append("FFMPEG_NOT_INSTALLED")
    if not fp: errors.append("FFPROBE_NOT_INSTALLED")

    if errors:
        fail(errors, warnings)

    result = {
        "status": "PLAN_PASS",
        "plan_beats": len(beats),
        "plan_shots": len(shots),
        "target_seconds": target,
        "output_exists": OUT.exists(),
        "output_bytes": OUT.stat().st_size if OUT.exists() else 0,
    }

    if OUT.exists() and OUT.stat().st_size >= 1024:
        probe = subprocess.run([
            fp, "-v", "error", "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height",
            "-of", "json", str(OUT)
        ], capture_output=True, text=True)
        if probe.returncode:
            fail(["OUTPUT_FFPROBE_FAILED"], [probe.stderr.strip()])
        meta = json.loads(probe.stdout)
        duration = float(meta.get("format", {}).get("duration", 0))
        streams = meta.get("streams", [])
        video = any(s.get("codec_type") == "video" and s.get("width") == 1920 and s.get("height") == 1080 for s in streams)
        audio = any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac" for s in streams)
        result.update({"duration_seconds": duration, "video_1080p": video, "audio_aac": audio})
        if duration < target - 2 or not video or not audio:
            fail(["OUTPUT_QC_FAILED"], [json.dumps(result, ensure_ascii=False)])
        result["status"] = "OUTPUT_PASS"

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()

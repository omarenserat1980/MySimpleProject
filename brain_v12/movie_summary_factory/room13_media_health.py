#!/usr/bin/env python3
"""Preflight gate for Room 13 media production.

Checks the Brain media toolchain, TTS availability, plan integrity, and
renderer/QC coupling before an expensive render starts.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
RENDERER = ROOT / "brain_v12/movie_summary_factory/render_room13_animatic.py"
QC = ROOT / "brain_v12/movie_summary_factory/room13_qc.py"


def main() -> int:
    checks = {}
    checks["ffmpeg"] = shutil.which("ffmpeg")
    checks["ffprobe"] = shutil.which("ffprobe")
    checks["espeak_ng"] = shutil.which("espeak-ng")
    checks["plan"] = PLAN.is_file()
    checks["renderer"] = RENDERER.is_file()
    checks["qc"] = QC.is_file()

    if checks["espeak_ng"]:
        p = subprocess.run(
            ["espeak-ng", "--voices"],
            check=True, text=True, capture_output=True
        )
        checks["arabic_voice"] = any(
            line.split() and "ar" in line.split()[:4]
            for line in p.stdout.splitlines()
        )
    else:
        checks["arabic_voice"] = False

    if checks["plan"]:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        checks["shots"] = len(plan.get("shots", []))
        checks["target_minutes"] = plan.get("target_minutes")
        checks["all_voice"] = all(s.get("voice") for s in plan.get("shots", []))
        checks["all_visuals"] = all(s.get("visual") for s in plan.get("shots", []))
    else:
        checks["shots"] = 0
        checks["target_minutes"] = 0
        checks["all_voice"] = False
        checks["all_visuals"] = False

    source = RENDERER.read_text(encoding="utf-8") if checks["renderer"] else ""
    checks["uses_brain_ffmpeg"] = "brain_ffmpeg" in source
    checks["uses_tts"] = "espeak-ng" in source
    checks["creates_visual_assets"] = "make_ppm" in source
    checks["rejects_bad_output"] = "ROOM13_QC_FAILED" in source

    failed = [k for k, v in checks.items() if v in (False, None, "", 0)]
    result = {"status": "READY" if not failed else "BLOCKED",
              "checks": checks, "failed": failed}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())

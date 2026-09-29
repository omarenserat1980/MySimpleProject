#!/usr/bin/env python3
"""Brain Cloud Cinematic Autopilot.

Deterministic production supervisor:
preflight -> tests -> clean partial state -> render -> QC -> manifest.
It retries transient render failures without declaring success until the MP4
passes the same QC gate used by the production workflow.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "brain_v12/movie_summary_factory/jobs/room-13-horror-10m-cinematic-v3.json"
RENDER = ROOT / "brain_v12/movie_summary_factory/render_room13_animatic.py"
QC = ROOT / "brain_v12/movie_summary_factory/room13_qc.py"
TEST = ROOT / "brain_v12/movie_summary_factory/test_room13_pipeline.py"
ENGINE = ROOT / "brain_v12/web/media/engine"
OUT = ENGINE / "room-13-horror-10m-animatic.mp4"
STATE = ENGINE / "cinematic-autopilot-state.json"
FINAL = ROOT / "cinematic_output" / "final.mp4"
LOG = ROOT / "cinematic_output" / "cinematic-autopilot.log"

MAX_ATTEMPTS = max(1, min(5, int(os.getenv("CINEMATIC_MAX_ATTEMPTS", "3"))))


def run(cmd: list[str], log) -> int:
    log.write("\n$ " + " ".join(cmd) + "\n")
    p = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True)
    return p.wait()


def write_state(status: str, attempt: int, **extra) -> None:
    ENGINE.mkdir(parents=True, exist_ok=True)
    data = {"status": status, "attempt": attempt, "max_attempts": MAX_ATTEMPTS,
            "updated_at": time.time(), "output": str(FINAL)}
    data.update(extra)
    STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_partial() -> None:
    for pattern in ("room13-segment-*.mp4", "room13-concat.txt"):
        for p in ENGINE.glob(pattern):
            p.unlink(missing_ok=True)
    for p in (OUT, ENGINE / "room-13-qc.json", ENGINE / "room-13-progress.json"):
        p.unlink(missing_ok=True)


def main() -> int:
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    ENGINE.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    if not PLAN.is_file():
        write_state("FAILED", 0, error="PLAN_NOT_FOUND")
        return 2

    with LOG.open("w", encoding="utf-8") as log:
        write_state("PREFLIGHT", 0)
        rc = run([sys.executable, "-m", "unittest", "brain_v12.movie_summary_factory.test_room13_pipeline", "-v"], log)
        if rc != 0:
            write_state("FAILED", 0, error="DETERMINISTIC_TESTS_FAILED")
            return rc

        rc = run([sys.executable, "brain_v12/movie_summary_factory/room13_media_health.py"], log)
        if rc != 0:
            write_state("FAILED", 0, error="MEDIA_HEALTH_GATE_FAILED")
            return rc

        for attempt in range(1, MAX_ATTEMPTS + 1):
            write_state("RENDERING", attempt)
            clean_partial()
            rc = run([sys.executable, str(RENDER)], log)
            if rc != 0:
                write_state("RETRYING" if attempt < MAX_ATTEMPTS else "FAILED",
                            attempt, error=f"RENDER_FAILED_RC_{rc}")
                continue

            write_state("VERIFYING", attempt)
            rc = run([sys.executable, str(QC)], log)
            if rc != 0:
                write_state("RETRYING" if attempt < MAX_ATTEMPTS else "FAILED",
                            attempt, error=f"QC_FAILED_RC_{rc}")
                continue

            if not OUT.is_file() or OUT.stat().st_size < 1024:
                write_state("RETRYING" if attempt < MAX_ATTEMPTS else "FAILED",
                            attempt, error="OUTPUT_MISSING_OR_TOO_SMALL")
                continue

            FINAL.write_bytes(OUT.read_bytes())
            manifest = {
                "status": "VERIFIED_COMPLETED",
                "profile": "BRAIN CLOUD CINEMATIC AUTOPILOT",
                "runtime": "brain_cloud",
                "device_required": False,
                "termux_required": False,
                "plan": str(PLAN.relative_to(ROOT)),
                "video": str(FINAL.relative_to(ROOT)),
                "bytes": FINAL.stat().st_size,
                "attempt": attempt,
                "verified_by": str(QC.relative_to(ROOT)),
            }
            (FINAL.parent / "film_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            write_state("VERIFIED_COMPLETED", attempt, video=str(FINAL), bytes=FINAL.stat().st_size)
            print(json.dumps(manifest, ensure_ascii=False))
            return 0

    write_state("FAILED", MAX_ATTEMPTS, error="EXHAUSTED_RETRIES")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

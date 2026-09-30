#!/usr/bin/env python3
"""Infinite Brain code-evolution supervisor.

Each cycle performs up to 100,000,000 review iterations. A failed verification
creates evidence and invokes the repair engine. A repair is accepted only after
the verification gate passes. The outer cycle never ends unless explicitly
limited with --cycles.

This process is designed for a persistent Brain runtime. GitHub Actions should
use the bounded review_loop.py because hosted jobs have finite lifetimes.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
REVIEW = ROOT / "brain_v12" / "self_healing" / "review_loop.py"
REPAIR = ROOT / "brain_v12" / "self_healing" / "repair.py"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def execute(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def run_review(loops: int, timeout: int) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("BRAIN_PROACTIVE_EVOLUTION", "1")
    p = subprocess.run([
        env.get("PYTHON", "python"), str(REVIEW),
        "--loops", str(loops), "--timeout", str(timeout)
    ], cwd=ROOT, env=env, text=True, capture_output=True, timeout=max(timeout, 120) * min(loops, 100))
    return p.returncode, p.stdout[-16000:], p.stderr[-16000:]


def repair_after_failure(timeout: int) -> tuple[int, str, str]:
    failure = STATE / "current_failure.json"
    env = os.environ.copy()
    env["BRAIN_FAILURE_FILE"] = str(failure)
    p = subprocess.run(
        [env.get("PYTHON", "python"), str(REPAIR)],
        cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout
    )
    return p.returncode, p.stdout[-12000:], p.stderr[-12000:]


def append_event(event: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    path = STATE / "continuous_evolution_history.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops-per-cycle", type=int,
                    default=int(os.getenv("BRAIN_LOOPS_PER_CYCLE", "100000000")))
    ap.add_argument("--pause", type=float,
                    default=float(os.getenv("BRAIN_CYCLE_PAUSE_SECONDS", "5")))
    ap.add_argument("--timeout", type=int,
                    default=int(os.getenv("BRAIN_REVIEW_TIMEOUT", "120")))
    ap.add_argument("--cycles", type=int, default=0,
                    help="0 = infinite cycles")
    args = ap.parse_args()

    if not 1 <= args.loops_per_cycle <= 100000000:
        raise SystemExit("--loops-per-cycle must be between 1 and 100000000")
    if args.cycles < 0:
        raise SystemExit("--cycles must be >= 0")

    STATE.mkdir(parents=True, exist_ok=True)
    cycle = 0

    while args.cycles == 0 or cycle < args.cycles:
        cycle += 1
        started = now()
        repair_code = None
        repair_stdout = ""
        repair_stderr = ""

        try:
            code, stdout, stderr = run_review(args.loops_per_cycle, args.timeout)
        except Exception as exc:
            code, stdout, stderr = 124, "", repr(exc)

        # A failed review cycle gets an additional repair opportunity.
        if code != 0:
            try:
                repair_code, repair_stdout, repair_stderr = repair_after_failure(args.timeout)
            except Exception as exc:
                repair_code, repair_stdout, repair_stderr = 124, "", repr(exc)

        status = "VERIFIED" if code == 0 else "REPAIR_ATTEMPTED"
        append_event({
            "schema": "brain-infinite-evolution/v2",
            "cycle": cycle,
            "started_at": started,
            "finished_at": now(),
            "loops_per_cycle": args.loops_per_cycle,
            "review_exit_code": code,
            "review_stdout": stdout,
            "review_stderr": stderr,
            "repair_exit_code": repair_code,
            "repair_stdout": repair_stdout,
            "repair_stderr": repair_stderr,
            "status": status,
        })
        print(
            f"BRAIN_EVOLUTION cycle={cycle} "
            f"loops={args.loops_per_cycle} status={status}",
            flush=True,
        )

        if args.pause:
            time.sleep(args.pause)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

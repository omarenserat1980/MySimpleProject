#!/usr/bin/env python3
"""Brain continuous evolution daemon.

Runs forever by default. Every cycle contains up to 1000 review loops.
A failed verification produces evidence, invokes the Brain repair engine, and
re-verifies the result. The daemon never treats generated code as successful
until the verification gate passes.

For GitHub Actions, use review_loop.py in bounded jobs; this daemon is intended
for a persistent Brain runtime/agent.
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_review(loops: int, timeout: int) -> tuple[int, str, str]:
    p = subprocess.run(
        [os.environ.get("PYTHON", "python"), str(REVIEW), "--loops", str(loops),
         "--timeout", str(timeout)],
        cwd=ROOT, text=True, capture_output=True
    )
    return p.returncode, p.stdout[-12000:], p.stderr[-12000:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops-per-cycle", type=int,
                    default=int(os.getenv("BRAIN_LOOPS_PER_CYCLE", "100000000")))
    ap.add_argument("--pause", type=float,
                    default=float(os.getenv("BRAIN_CYCLE_PAUSE_SECONDS", "5")))
    ap.add_argument("--timeout", type=int,
                    default=int(os.getenv("BRAIN_REVIEW_TIMEOUT", "120")))
    ap.add_argument("--cycles", type=int, default=0,
                    help="0 means forever")
    args = ap.parse_args()

    if not 1 <= args.loops_per_cycle <= 100000000:
        raise SystemExit("--loops-per-cycle must be between 1 and 100000000")
    if args.cycles < 0:
        raise SystemExit("--cycles must be >= 0")

    STATE.mkdir(parents=True, exist_ok=True)
    cycle = 0
    history_path = STATE / "continuous_evolution_history.jsonl"

    while args.cycles == 0 or cycle < args.cycles:
        cycle += 1
        started = now()
        code, stdout, stderr = run_review(args.loops_per_cycle, args.timeout)
        record = {
            "schema": "brain-continuous-evolution/v1",
            "cycle": cycle,
            "started_at": started,
            "finished_at": now(),
            "loops_per_cycle": args.loops_per_cycle,
            "exit_code": code,
            "status": "VERIFIED" if code == 0 else "REPAIR_REQUIRED_OR_FAILED",
            "stdout": stdout,
            "stderr": stderr,
        }
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        print(
            f"BRAIN_EVOLUTION cycle={cycle} "
            f"loops={args.loops_per_cycle} status={record['status']}",
            flush=True,
        )

        # Never stop the long-lived Brain because one repair cycle failed.
        # The next cycle starts a fresh review and gets another repair opportunity.
        if args.pause:
            time.sleep(args.pause)


if __name__ == "__main__":
    raise SystemExit(main())

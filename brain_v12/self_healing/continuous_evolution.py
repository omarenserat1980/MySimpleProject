#!/usr/bin/env python3
"""Bounded or persistent Brain code-evolution supervisor.

Each cycle performs a verified review. A failed review gets a repair
opportunity and a post-repair verification. Hosted automation should use a
small bounded --cycles value; a persistent Brain runtime may use --cycles 0.
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
REVIEW = "brain_v12.self_healing.review_loop"
REPAIR = "brain_v12.self_healing.repair"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_module(module: str, args: list[str], timeout: int) -> tuple[int, str, str]:
    env = os.environ.copy()
    env.setdefault("BRAIN_PROACTIVE_EVOLUTION", "1")
    p = subprocess.run(
        [env.get("PYTHON", "python"), "-m", module, *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return p.returncode, p.stdout[-16000:], p.stderr[-16000:]


def run_review(loops: int, timeout: int) -> tuple[int, str, str]:
    return run_module(REVIEW, ["--loops", str(loops), "--timeout", str(timeout)], max(timeout, 120) * min(loops, 100))


def repair_after_failure(timeout: int) -> tuple[int, str, str]:
    failure = STATE / "current_failure.json"
    env = os.environ.copy()
    env["BRAIN_FAILURE_FILE"] = str(failure)
    p = subprocess.run(
        [env.get("PYTHON", "python"), "-m", REPAIR],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return p.returncode, p.stdout[-12000:], p.stderr[-12000:]


def append_event(event: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "continuous_evolution_history.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops-per-cycle", type=int, default=int(os.getenv("BRAIN_LOOPS_PER_CYCLE", "1")))
    ap.add_argument("--pause", type=float, default=float(os.getenv("BRAIN_CYCLE_PAUSE_SECONDS", "5")))
    ap.add_argument("--timeout", type=int, default=int(os.getenv("BRAIN_REVIEW_TIMEOUT", "120")))
    ap.add_argument("--cycles", type=int, default=0, help="0 = infinite cycles")
    args = ap.parse_args()

    if not 1 <= args.loops_per_cycle <= 100000000:
        raise SystemExit("--loops-per-cycle must be between 1 and 100000000")
    if args.cycles < 0:
        raise SystemExit("--cycles must be >= 0")

    STATE.mkdir(parents=True, exist_ok=True)
    checkpoint = STATE / "evolution_checkpoint.json"
    try:
        cycle = int(json.loads(checkpoint.read_text(encoding="utf-8")).get("cycle", 0)) if checkpoint.is_file() else 0
    except Exception:
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

        if code != 0:
            try:
                repair_code, repair_stdout, repair_stderr = repair_after_failure(args.timeout)
            except Exception as exc:
                repair_code, repair_stdout, repair_stderr = 124, "", repr(exc)

        if code != 0 and repair_code == 0:
            try:
                verify_code, verify_out, verify_err = run_review(1, args.timeout)
                code = verify_code
                stdout += "\nPOST_REPAIR_REVERIFY\n" + verify_out
                stderr += "\nPOST_REPAIR_REVERIFY\n" + verify_err
            except Exception as exc:
                code, stdout, stderr = 124, stdout, stderr + "\nPOST_REPAIR_REVERIFY_ERROR=" + repr(exc)

        status = "VERIFIED" if code == 0 else "FAILED"
        append_event({
            "schema": "brain-infinite-evolution/v3",
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
        checkpoint.write_text(
            json.dumps(
                {
                    "schema": "brain-evolution-checkpoint/v2",
                    "cycle": cycle,
                    "status": status,
                    "updated_at": now(),
                    "review_exit_code": code,
                    "repair_exit_code": repair_code,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"BRAIN_EVOLUTION cycle={cycle} loops={args.loops_per_cycle} status={status}", flush=True)
        if code != 0:
            print("BRAIN_EVOLUTION_REVIEW_STDOUT=" + stdout[-4000:], flush=True)
            print("BRAIN_EVOLUTION_REVIEW_STDERR=" + stderr[-4000:], flush=True)
            if repair_code is not None:
                print("BRAIN_EVOLUTION_REPAIR_EXIT=" + str(repair_code), flush=True)
                print("BRAIN_EVOLUTION_REPAIR_STDOUT=" + repair_stdout[-4000:], flush=True)
                print("BRAIN_EVOLUTION_REPAIR_STDERR=" + repair_stderr[-4000:], flush=True)

        if code != 0:
            return code
        if args.pause:
            time.sleep(args.pause)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

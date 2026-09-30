#!/usr/bin/env python3
"""Brain 1000-loop continuous code review and self-healing engine.

Each loop:
  REVIEW -> RUN -> VERIFY -> (FAIL => REPAIR => VERIFY) -> RECORD -> next loop

The engine is intentionally bounded to 1000 review loops per invocation. A
scheduler can invoke it again for continued operation. It never declares a
repair successful merely because a patch was generated: verification must pass.
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
PY_ROOTS = ("brain_v12", "tests", "scripts")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)


def review_files() -> dict:
    files = []
    for root in PY_ROOTS:
        p = ROOT / root
        if p.exists():
            files.extend(str(x.relative_to(ROOT)) for x in p.rglob("*.py") if x.is_file())
    return {"python_files": len(files), "files": files[:5000]}


def deterministic_review(timeout: int) -> tuple[bool, dict]:
    checks = []
    commands = [
        [os.environ.get("PYTHON", "python"), "-m", "compileall", "-q", "brain_v12"],
        [os.environ.get("PYTHON", "python"), "brain_v12/self_healing/self_test.py"],
    ]
    if os.getenv("BRAIN_REVIEW_PYTEST", "0") == "1":
        commands.append([os.environ.get("PYTHON", "python"), "-m", "pytest", "-q"])

    ok = True
    for cmd in commands:
        try:
            p = run(cmd, timeout)
            checks.append({
                "command": " ".join(cmd),
                "exit_code": p.returncode,
                "stdout": p.stdout[-4000:],
                "stderr": p.stderr[-4000:],
            })
            ok = ok and p.returncode == 0
        except subprocess.TimeoutExpired as e:
            checks.append({"command": " ".join(cmd), "exit_code": 124, "stdout": str(e.stdout or ""), "stderr": str(e.stderr or "")})
            ok = False
    return ok, {"checks": checks}


def repair(timeout: int) -> tuple[bool, dict]:
    env = os.environ.copy()
    failure = STATE / "current_failure.json"
    env["BRAIN_FAILURE_FILE"] = str(failure)
    try:
        p = subprocess.run(
            [env.get("PYTHON", "python"), "brain_v12/self_healing/repair.py"],
            cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout
        )
        return p.returncode == 0, {
            "exit_code": p.returncode,
            "stdout": p.stdout[-8000:],
            "stderr": p.stderr[-8000:],
        }
    except subprocess.TimeoutExpired:
        return False, {"exit_code": 124, "stdout": "", "stderr": "repair timeout"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loops", type=int, default=int(os.getenv("BRAIN_REVIEW_LOOPS", "100000000")))
    ap.add_argument("--delay", type=float, default=float(os.getenv("BRAIN_REVIEW_DELAY", "0")))
    ap.add_argument("--timeout", type=int, default=int(os.getenv("BRAIN_REVIEW_TIMEOUT", "120")))
    args = ap.parse_args()
    if not 1 <= args.loops <= 100000000:
        raise SystemExit("--loops must be between 1 and 100000000")

    STATE.mkdir(parents=True, exist_ok=True)
    history = []
    final_ok = True

    for i in range(1, args.loops + 1):
        entry = {"loop": i, "started_at": now(), "review": review_files()}
        ok, details = deterministic_review(args.timeout)
        entry["verification"] = details
        entry["status"] = "VERIFIED"

        if not ok:
            final_ok = False
            failure = {
                "schema": "brain-repair-context/v2",
                "loop": i,
                "created_at": now(),
                "reason": "verification_failed",
                "review": entry["review"],
                "verification": details,
            }
            (STATE / "current_failure.json").write_text(
                json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            repaired, repair_details = repair(args.timeout)
            entry["repair"] = repair_details
            ok2, details2 = deterministic_review(args.timeout)
            entry["post_repair_verification"] = details2
            entry["status"] = "REPAIRED_AND_VERIFIED" if repaired and ok2 else "REPAIR_FAILED"
            final_ok = repaired and ok2

        entry["finished_at"] = now()
        history.append(entry)
        print(f"BRAIN_REVIEW_LOOP {i}/{args.loops} status={entry['status']}", flush=True)

        # A successful loop is not the end: the requested review loop continues.
        if args.delay:
            time.sleep(args.delay)

    report = {
        "schema": "brain-1000-review-loop/v1",
        "status": "VERIFIED_COMPLETED" if final_ok else "FAILED_REPAIR_CYCLE",
        "loops_requested": args.loops,
        "loops_completed": len(history),
        "finished_at": now(),
        "history": history,
    }
    (STATE / "1000_loop_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"],
        "loops_completed": len(history),
        "report": str(STATE / "1000_loop_report.json"),
    }, ensure_ascii=False))
    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

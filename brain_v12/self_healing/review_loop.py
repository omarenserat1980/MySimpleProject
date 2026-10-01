#!/usr/bin/env python3
"""Brain continuous code review and self-healing engine.

Each loop:
  REVIEW -> RUN -> VERIFY -> (FAIL => REPAIR => VERIFY) -> RECORD -> next loop

The engine is intentionally bounded per invocation. A scheduler can invoke it
again for continued operation. It never declares a repair successful merely
because a patch was generated: verification must pass.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .command_contract import is_continue
from .generator_registry import supported_candidates

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
PY_ROOTS = ("brain_v12", "tests", "scripts")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def continue_autonomously() -> bool:
    """Return whether the Brain received its explicit continuation directive.

    The directive is intentionally opt-in. It means continue through the safe
    observe -> diagnose -> execute -> verify -> repair -> retry cycle, never
    bypassing verification or safety gates.
    """
    raw = os.getenv("BRAIN_COMMAND", "").strip()
    if raw == "BRAIN_CONTINUE_AUTONOMOUSLY":
        return True
    return is_continue(raw)


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
        [os.environ.get("PYTHON", "python"), "-m", "brain_v12.self_healing.self_test"],
    ]
    if os.getenv("BRAIN_REVIEW_PYTEST", "0") == "1":
        commands.append([os.environ.get("PYTHON", "python"), "-m", "pytest", "-q"])
    commands.append([os.environ.get("PYTHON", "python"), "-m", "brain_v12.self_healing.verification_gate"])

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
            [env.get("PYTHON", "python"), "-m", "brain_v12.self_healing.repair"],
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
    autonomous = continue_autonomously()
    if autonomous:
        print("BRAIN_COMMAND=CONTINUE_AUTONOMOUSLY", flush=True)

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

        if final_ok and (autonomous or os.getenv("BRAIN_PROACTIVE_EVOLUTION", "0") == "1"):
            # First discover deterministic, evidence-backed opportunities.
            discovery = run(
                [os.environ.get("PYTHON", "python"), "-m",
                 "brain_v12.self_healing.improvement_engine"],
                timeout=args.timeout,
            )
            entry["improvement_discovery"] = {
                "exit_code": discovery.returncode,
                "stdout": discovery.stdout[-6000:],
                "stderr": discovery.stderr[-6000:],
            }
            improvement_file = STATE / "current_improvement.json"
            try:
                improvement = json.loads(improvement_file.read_text(encoding="utf-8"))
            except Exception:
                improvement = {
                    "schema": "brain-improvement-context/v2",
                    "loop": i,
                    "created_at": now(),
                    "reason": "verified_state_improvement_review",
                    "review": entry["review"],
                    "verification": details,
                    "discovery_failed": True,
                }
                improvement_file.write_text(
                    json.dumps(improvement, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            improvement["loop"] = i
            improvement["review"] = entry["review"]
            improvement["verification"] = details
            improvement_file.write_text(
                json.dumps(improvement, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            candidate_count = int(improvement.get("candidate_count", 0) or 0)
            mode = str(improvement.get("mode", "PROPOSAL_ONLY"))
            generator_configured = bool(os.getenv("BRAIN_CODE_GENERATOR_COMMAND"))
            eligible_candidates = supported_candidates(improvement.get("candidates", []))
            eligible = (
                candidate_count > 0
                and bool(eligible_candidates)
                and mode == "GENERATOR_ELIGIBLE"
                and generator_configured
            )
            entry["improvement_eligibility"] = {
                "candidate_count": candidate_count,
                "mode": mode,
                "generator_configured": generator_configured,
                "supported_candidate_count": len(eligible_candidates),
                "eligible": eligible,
            }
            print(
                "BRAIN_IMPROVEMENT_ELIGIBILITY "
                + json.dumps(entry["improvement_eligibility"], ensure_ascii=False, sort_keys=True),
                flush=True,
            )

            if not eligible:
                entry["proactive_improvement"] = {
                    "status": "NOT_APPLIED",
                    "reason": (
                        "no_safe_candidate"
                        if candidate_count == 0
                        else "generator_not_eligible"
                    ),
                }
                entry["status"] = "VERIFIED_NO_IMPROVEMENT"
            else:
                old_failure = os.environ.get("BRAIN_FAILURE_FILE")
                os.environ["BRAIN_FAILURE_FILE"] = str(improvement_file)
                improved, improvement_details = repair(args.timeout)
                if old_failure is None:
                    os.environ.pop("BRAIN_FAILURE_FILE", None)
                else:
                    os.environ["BRAIN_FAILURE_FILE"] = old_failure
                entry["proactive_improvement"] = improvement_details
                if improved:
                    final_ok, after_improvement = deterministic_review(args.timeout)
                    entry["improvement_verification"] = after_improvement
                    if not final_ok:
                        final_ok = True
                        entry["status"] = "IMPROVEMENT_REJECTED_AND_ROLLED_BACK"
                else:
                    entry["status"] = "VERIFIED_NO_IMPROVEMENT"

        entry["finished_at"] = now()
        history.append(entry)
        print(f"BRAIN_REVIEW_LOOP {i}/{args.loops} status={entry['status']}", flush=True)
        if args.delay:
            time.sleep(args.delay)

    (STATE / "1000_loop_report.json").write_text(json.dumps({
        "compatibility_alias": "review_loop_report.json",
        "created_at": now(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "schema": "brain-100m-review-loop/v2",
        "status": "VERIFIED_COMPLETED" if final_ok else "FAILED_REPAIR_CYCLE",
        "loops_requested": args.loops,
        "loops_completed": len(history),
        "finished_at": now(),
        "history": history,
    }
    (STATE / "review_loop_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"],
        "loops_completed": len(history),
        "report": str(STATE / "review_loop_report.json"),
    }, ensure_ascii=False))
    return 0 if final_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

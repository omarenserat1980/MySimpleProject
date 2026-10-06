#!/usr/bin/env python3
"""Bounded continuous evolution guardian for CL-000003 on Arkan.

Scope is deliberately limited to the CL-000003 industrial quote portal and its
direct tests. It never performs purchases, payments, contracts, deployments,
or Git pushes. Repairs are accepted only when post-repair verification passes;
otherwise the candidate patch is rolled back.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
HISTORY = STATE / "cl_000003_arkan_evolution.jsonl"
FAILURE = STATE / "cl_000003_current_failure.json"
PATCH = STATE / "last_applied_patch.diff"

TARGET_FILES = [
    "brain_v12/brain/industrial_quote_portal.py",
    "brain_v12/tests/test_industrial_quote_portal.py",
    "brain_v12/web/industrial-quote-portal/index.html",
    "brain_v12/web/industrial-quote-portal/admin.html",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(cmd: list[str], timeout: int = 180) -> dict:
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    return {
        "command": cmd,
        "exit_code": p.returncode,
        "stdout": p.stdout[-12000:],
        "stderr": p.stderr[-12000:],
    }


def verify() -> tuple[bool, list[dict]]:
    checks = [
        run([sys.executable, "-m", "py_compile",
             "brain_v12/brain/industrial_quote_portal.py",
             "brain_v12/tests/test_industrial_quote_portal.py"]),
        run([sys.executable, "-m", "pytest",
             "brain_v12/tests/test_industrial_quote_portal.py", "-q"]),
        run(["git", "diff", "--check"]),
    ]
    return all(x["exit_code"] == 0 for x in checks), checks


def write_failure(checks: list[dict]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    FAILURE.write_text(json.dumps({
        "schema": "cl-000003-arkan-failure/v1",
        "client_id": "CL-000003",
        "device": "Arkan",
        "created_at": now(),
        "scope": TARGET_FILES,
        "checks": checks,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def rollback_patch() -> bool:
    if not PATCH.is_file():
        return True
    p = subprocess.run(
        ["git", "apply", "-R", "--whitespace=error-all", str(PATCH)],
        cwd=ROOT, text=True, capture_output=True,
    )
    if p.returncode == 0:
        PATCH.unlink(missing_ok=True)
        return True
    return False


def repair() -> dict:
    generator = os.getenv("BRAIN_CODE_GENERATOR_COMMAND", "").strip()
    proposal = STATE / "current_improvement.json"
    if not generator or not proposal.is_file():
        return {"attempted": False, "reason": "REPAIR_GENERATOR_OR_PROPOSAL_NOT_CONFIGURED"}

    env = os.environ.copy()
    env["BRAIN_FAILURE_FILE"] = str(FAILURE)
    env["BRAIN_REPAIR_ACTIONS"] = "compile,self-test,tests,gate"
    env["BRAIN_REPAIR_ROOTS"] = "brain_v12/"
    env["BRAIN_REPAIR_CANDIDATES"] = os.getenv("BRAIN_REPAIR_CANDIDATES", "3")
    p = subprocess.run(
        [sys.executable, "-m", "brain_v12.self_healing.repair"],
        cwd=ROOT, env=env, text=True, capture_output=True,
        timeout=int(os.getenv("BRAIN_REPAIR_TIMEOUT", "900")),
    )
    if p.returncode:
        return {
            "attempted": True, "exit_code": p.returncode,
            "stdout": p.stdout[-10000:], "stderr": p.stderr[-10000:],
            "verified": False,
        }

    ok, checks = verify()
    if ok:
        return {
            "attempted": True, "exit_code": 0, "verified": True,
            "checks": checks, "stdout": p.stdout[-10000:], "stderr": p.stderr[-10000:],
        }

    rolled_back = rollback_patch()
    return {
        "attempted": True, "exit_code": 1, "verified": False,
        "rolled_back": rolled_back, "checks": checks,
        "stdout": p.stdout[-10000:], "stderr": p.stderr[-10000:],
    }


def cycle() -> int:
    ok, checks = verify()
    repair_result = None
    status = "VERIFIED"
    if not ok:
        status = "FAILED"
        write_failure(checks)
        repair_result = repair()
        if repair_result.get("verified"):
            ok = True
            status = "REPAIRED_AND_VERIFIED"

    event = {
        "schema": "cl-000003-arkan-evolution/v1",
        "timestamp": now(),
        "client_id": "CL-000003",
        "device": "Arkan",
        "status": status,
        "verified": ok,
        "scope": TARGET_FILES,
        "checks": checks,
        "repair": repair_result,
        "financial_actions": False,
        "contract_actions": False,
        "deployment_actions": False,
        "git_push": False,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print("CL3_ARKAN_EVOLUTION=" + json.dumps(event, ensure_ascii=False), flush=True)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=0, help="0 = continuous")
    ap.add_argument("--pause", type=int, default=int(os.getenv("CL3_EVOLUTION_PAUSE_SECONDS", "300")))
    args = ap.parse_args()
    if args.cycles < 0 or args.pause < 0:
        raise SystemExit("cycles and pause must be >= 0")

    count = 0
    while args.cycles == 0 or count < args.cycles:
        count += 1
        if cycle() != 0:
            return 1
        if args.cycles == 0 or count < args.cycles:
            time.sleep(args.pause)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

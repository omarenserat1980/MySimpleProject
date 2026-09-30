#!/usr/bin/env python3
"""Evidence-driven repair dispatcher with candidate verification and rollback.

A generated patch is never considered successful by itself. Each candidate is
tested locally; failed candidates are reversed before the next candidate.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATCH_FILE = ROOT / ".brain" / "state" / "last_applied_patch.diff"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def verify(actions: list[str]) -> tuple[bool, list[dict]]:
    allowed = {
        "compile": [sys.executable, "-m", "compileall", "-q", "brain_v12"],
        "self-test": [sys.executable, "brain_v12/self_healing/self_test.py"],
        "tests": [sys.executable, "-m", "pytest", "-q"],
        "gate": [sys.executable, "brain_v12/self_healing/verification_gate.py"],
    }
    results = []
    for name in actions:
        if name not in allowed:
            results.append({"action": name, "exit_code": 2, "error": "not_allowed"})
            return False, results
        p = run(allowed[name])
        results.append({
            "action": name,
            "exit_code": p.returncode,
            "stdout": p.stdout[-6000:],
            "stderr": p.stderr[-6000:],
        })
        if p.returncode != 0:
            return False, results
    return True, results


def rollback() -> bool:
    if not PATCH_FILE.is_file():
        return True
    p = subprocess.run(
        ["git", "apply", "-R", "--whitespace=error-all", str(PATCH_FILE)],
        cwd=ROOT, text=True, capture_output=True,
    )
    if p.returncode != 0:
        print(p.stderr[-12000:], file=sys.stderr)
        return False
    PATCH_FILE.unlink(missing_ok=True)
    return True


def main() -> int:
    actions = [x.strip() for x in os.getenv(
        "BRAIN_REPAIR_ACTIONS", "compile,self-test"
    ).split(",") if x.strip()]
    candidates = max(1, min(3, int(os.getenv("BRAIN_REPAIR_CANDIDATES", "3"))))
    generator = os.getenv("BRAIN_CODE_GENERATOR_COMMAND")
    failure = os.getenv("BRAIN_FAILURE_FILE")

    if generator and failure:
        env = os.environ.copy()
        env["BRAIN_FAILURE_FILE"] = failure

        for candidate in range(1, candidates + 1):
            # Never let a previous failed candidate contaminate the next one.
            if PATCH_FILE.is_file():
                if not rollback():
                    print("REPAIR_ROLLBACK_FAILED", file=sys.stderr)
                    return 3

            print(f"REPAIR_CANDIDATE={candidate}")
            agent = subprocess.run(
                [sys.executable, "brain_v12/self_healing/code_repair_agent.py"],
                cwd=ROOT, env=env, text=True, capture_output=True,
                timeout=int(os.getenv("BRAIN_GENERATOR_TIMEOUT", "600")),
            )
            if agent.stdout:
                print(agent.stdout[-12000:])
            if agent.returncode != 0:
                if agent.stderr:
                    print(agent.stderr[-12000:], file=sys.stderr)
                continue

            ok, results = verify(actions)
            print(f"REPAIR_CANDIDATE_{candidate}_VERIFIED={ok}")
            if ok:
                print("REPAIR_DISPATCH=VERIFIED")
                return 0

            print(json_safe(results))
            if not rollback():
                print("REPAIR_ROLLBACK_FAILED", file=sys.stderr)
                return 3

        print("REPAIR_ALL_CANDIDATES_FAILED", file=sys.stderr)
        return 1

    ok, results = verify(actions)
    print(json_safe(results))
    print("REPAIR_DISPATCH=VERIFIED" if ok else "REPAIR_DISPATCH=FAILED")
    return 0 if ok else 1


def json_safe(value: object) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


if __name__ == "__main__":
    raise SystemExit(main())

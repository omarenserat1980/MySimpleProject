#!/usr/bin/env python3
"""Evidence-driven, reversible code repair agent."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from brain_v12.self_healing.generator_registry import candidate_valid, contract

DEFAULT_ROOTS = ("brain_v12/", "tests/", "scripts/")
STATE = Path(".brain/state")
PATCH_FILE = STATE / "last_applied_patch.diff"


def fail(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def changed_paths(diff: str) -> list[str]:
    paths = []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            paths.append(line[6:].strip())
        elif line.startswith("--- a/") and line[6:].strip() != "/dev/null":
            paths.append(line[6:].strip())
    return sorted(set(paths))


def main() -> int:
    failure = os.getenv("BRAIN_FAILURE_FILE")
    context = os.getenv("BRAIN_REPAIR_CONTEXT", "failure")
    generator = os.getenv("BRAIN_CODE_GENERATOR_COMMAND")
    if not failure and context != "improvement":
        return fail("CODE_REPAIR_FAILURE_FILE_MISSING", 2)
    if not generator:
        return fail("CODE_REPAIR_GENERATOR_NOT_CONFIGURED", 2)
    if failure and not Path(failure).is_file() and context != "improvement":
        return fail("CODE_REPAIR_FAILURE_FILE_NOT_FOUND", 2)

    roots = tuple(
        x.strip().replace("\\", "/")
        for x in os.getenv("BRAIN_REPAIR_ROOTS", ",".join(DEFAULT_ROOTS)).split(",")
        if x.strip()
    )

    proposal = Path(".brain/state/current_improvement.json")
    if not proposal.is_file():
        return fail("CODE_REPAIR_PROPOSAL_MISSING", 2)
    try:
        data = json.loads(proposal.read_text(encoding="utf-8"))
    except Exception:
        return fail("CODE_REPAIR_PROPOSAL_INVALID", 2)

    candidates = [c for c in data.get("candidates", []) if candidate_valid(c)]
    if not candidates:
        return fail("CODE_REPAIR_NO_CONTRACT_VALID_CANDIDATE", 2)

    candidate_id = str(candidates[0].get("id"))
    spec = contract(candidate_id)
    if not spec:
        return fail("CODE_REPAIR_CONTRACT_MISSING", 2)

    env = os.environ.copy()
    if failure:
        env["BRAIN_REPAIR_FAILURE_FILE"] = str(Path(failure))
    env["BRAIN_REPAIR_CONTEXT"] = context
    env["BRAIN_GENERATOR_CANDIDATE_ID"] = candidate_id
    env.setdefault("BRAIN_REPAIR_CANDIDATE", os.getenv("BRAIN_REPAIR_CANDIDATE", "1"))

    try:
        p = subprocess.run(
            generator,
            shell=True,
            text=True,
            capture_output=True,
            timeout=int(os.getenv("BRAIN_GENERATOR_TIMEOUT", "600")),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return fail("CODE_REPAIR_GENERATOR_TIMEOUT", 124)

    if p.returncode:
        return fail(f"CODE_REPAIR_GENERATOR_FAILED={p.returncode}", p.returncode)

    diff = p.stdout.strip()
    if not (diff.startswith("diff --git ") or diff.startswith("--- ")):
        return fail("CODE_REPAIR_INVALID_DIFF_FORMAT", 2)

    paths = changed_paths(diff)
    if not paths:
        return fail("CODE_REPAIR_NO_CHANGED_FILES", 2)

    forbidden = [
        x for x in paths
        if Path(x).is_absolute()
        or not any(x == r.rstrip("/") or x.startswith(r) for r in roots)
    ]
    if forbidden:
        return fail("CODE_REPAIR_FORBIDDEN_PATHS=" + ",".join(forbidden), 2)

    if len(paths) > int(spec.get("max_changed_files", 1)):
        return fail("CODE_REPAIR_TOO_MANY_CHANGED_FILES", 2)

    contract_roots = tuple(spec.get("roots", ()))
    contract_forbidden = [
        x for x in paths
        if not any(x == r.rstrip("/") or x.startswith(r) for r in contract_roots)
    ]
    if contract_forbidden:
        return fail("CODE_REPAIR_CONTRACT_PATHS=" + ",".join(contract_forbidden), 2)

    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=error-all", "-"],
        input=diff,
        text=True,
        capture_output=True,
    )
    if check.returncode:
        return fail("CODE_REPAIR_PATCH_REJECTED", 2)

    applied = subprocess.run(
        ["git", "apply", "--whitespace=error-all", "-"],
        input=diff,
        text=True,
        capture_output=True,
    )
    if applied.returncode:
        return fail("CODE_REPAIR_APPLY_FAILED", applied.returncode)

    STATE.mkdir(parents=True, exist_ok=True)
    PATCH_FILE.write_text(diff + "\n", encoding="utf-8")
    print("CODE_REPAIR_APPLIED")
    print("CODE_REPAIR_CANDIDATE=" + env["BRAIN_REPAIR_CANDIDATE"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

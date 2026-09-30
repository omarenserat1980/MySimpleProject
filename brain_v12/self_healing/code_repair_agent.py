#!/usr/bin/env python3
"""Evidence-driven, reversible code repair agent.

A configured generator must emit a unified git diff. The patch is validated,
applied, and recorded so the supervisor can reverse it if verification fails.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

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
        elif line.startswith("--- a/"):
            path = line[6:].strip()
            if path != "/dev/null":
                paths.append(path)
    return sorted(set(paths))


def main() -> int:
    failure = os.getenv("BRAIN_FAILURE_FILE")
    generator = os.getenv("BRAIN_CODE_GENERATOR_COMMAND")
    if not failure:
        return fail("CODE_REPAIR_FAILURE_FILE_MISSING", 2)
    if not generator:
        return fail("CODE_REPAIR_GENERATOR_NOT_CONFIGURED", 2)

    failure_path = Path(failure)
    if not failure_path.is_file():
        return fail("CODE_REPAIR_FAILURE_FILE_NOT_FOUND", 2)

    roots = tuple(
        x.strip().replace("\\", "/")
        for x in os.getenv("BRAIN_REPAIR_ROOTS", ",".join(DEFAULT_ROOTS)).split(",")
        if x.strip()
    )

    env = os.environ.copy()
    env["BRAIN_REPAIR_FAILURE_FILE"] = str(failure_path)

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

    if p.returncode != 0:
        print(p.stderr[-12000:], file=sys.stderr)
        return fail(f"CODE_REPAIR_GENERATOR_FAILED={p.returncode}", p.returncode)

    diff = p.stdout.strip()
    if not (diff.startswith("diff --git ") or diff.startswith("--- ")):
        return fail("CODE_REPAIR_INVALID_DIFF_FORMAT", 2)

    paths = changed_paths(diff)
    if not paths:
        return fail("CODE_REPAIR_NO_CHANGED_FILES", 2)

    forbidden = [
        path for path in paths
        if Path(path).is_absolute() or not any(
            path == root.rstrip("/") or path.startswith(root) for root in roots
        )
    ]
    if forbidden:
        return fail("CODE_REPAIR_FORBIDDEN_PATHS=" + ",".join(forbidden), 2)

    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=error-all", "-"],
        input=diff,
        text=True,
        capture_output=True,
    )
    if check.returncode != 0:
        print(check.stderr[-12000:], file=sys.stderr)
        return fail("CODE_REPAIR_PATCH_REJECTED", 2)

    apply = subprocess.run(
        ["git", "apply", "--whitespace=error-all", "-"],
        input=diff,
        text=True,
        capture_output=True,
    )
    if apply.returncode != 0:
        print(apply.stderr[-12000:], file=sys.stderr)
        return fail("CODE_REPAIR_APPLY_FAILED", apply.returncode)

    STATE.mkdir(parents=True, exist_ok=True)
    PATCH_FILE.write_text(diff + "\n", encoding="utf-8")
    print("CODE_REPAIR_APPLIED")
    print("CODE_REPAIR_FILES=" + ",".join(paths))
    print("CODE_REPAIR_PATCH_FILE=" + str(PATCH_FILE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

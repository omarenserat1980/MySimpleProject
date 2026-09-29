#!/usr/bin/env python3
"""Stage 7 self-healing gate.

Runs before every cinematic production. It repairs only deterministic, known
registry syntax corruption, then compiles and validates the Stage 7 registry.
Unknown failures are blocked and reported instead of silently changing code.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "brain_v12/movie_summary_factory/room13_components.py"
MAX_REPAIRS = 3


def _compile(path: Path) -> tuple[bool, str]:
    p = subprocess.run([sys.executable, "-m", "py_compile", str(path)],
                       cwd=ROOT, text=True, capture_output=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip()


def repair_registry() -> list[str]:
    actions: list[str] = []
    text = REGISTRY.read_text(encoding="utf-8")
    repaired = re.sub(r"Component\(0([1-9]),", r"Component(\1,", text)
    if repaired != text:
        REGISTRY.write_text(repaired, encoding="utf-8")
        actions.append("normalized leading-zero component IDs")
    return actions


def main() -> int:
    if not REGISTRY.is_file():
        print(json.dumps({"status": "BLOCKED", "error": "REGISTRY_NOT_FOUND"}, ensure_ascii=False))
        return 2

    actions: list[str] = []
    last_error = ""
    for _ in range(MAX_REPAIRS):
        ok, err = _compile(REGISTRY)
        if ok:
            break
        last_error = err
        new_actions = repair_registry()
        if not new_actions:
            print(json.dumps({
                "status": "BLOCKED",
                "error": "UNSUPPORTED_STAGE7_SYNTAX",
                "details": last_error,
                "actions": actions,
            }, ensure_ascii=False, indent=2))
            return 2
        actions.extend(new_actions)
    else:
        print(json.dumps({
            "status": "BLOCKED",
            "error": "STAGE7_REPAIR_EXHAUSTED",
            "details": last_error,
            "actions": actions,
        }, ensure_ascii=False, indent=2))
        return 2

    verify = subprocess.run(
        [sys.executable, str(REGISTRY)],
        cwd=ROOT, text=True, capture_output=True
    )
    if verify.returncode != 0:
        print(json.dumps({
            "status": "BLOCKED",
            "error": "REGISTRY_VALIDATION_FAILED",
            "details": (verify.stdout + verify.stderr).strip(),
            "actions": actions,
        }, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps({
        "status": "READY",
        "stage": 7,
        "self_healing": True,
        "actions": actions,
        "message": "Stage 7 repaired/validated before cinematic production.",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

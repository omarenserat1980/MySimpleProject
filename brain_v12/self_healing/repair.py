#!/usr/bin/env python3
"""Conservative built-in repair dispatcher.

This module is intentionally deterministic. It does not invent arbitrary source
code. It checks common Brain failure modes and runs only explicit, local repair
actions. Advanced code synthesis can be plugged in through BRAIN_REPAIR_COMMAND
after review and verification.
"""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    actions = os.getenv("BRAIN_REPAIR_ACTIONS", "compile,self-test").strip()
    allowed = {
        "compile": [sys.executable, "-m", "compileall", "-q", "brain_v12"],
        "self-test": [sys.executable, "brain_v12/self_healing/self_test.py"],
        "tests": [sys.executable, "-m", "pytest", "-q"],
    }

    for name in [x.strip() for x in actions.split(",") if x.strip()]:
        if name not in allowed:
            print(f"REPAIR_ACTION_NOT_ALLOWED={name}", file=sys.stderr)
            return 2
        p = subprocess.run(allowed[name], text=True, capture_output=True)
        if p.stdout:
            print(p.stdout[-6000:])
        if p.stderr:
            print(p.stderr[-6000:], file=sys.stderr)
        if p.returncode != 0:
            return p.returncode

    print("REPAIR_DISPATCH=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

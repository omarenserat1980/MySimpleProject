#!/usr/bin/env python3
"""Conservative built-in repair dispatcher.

This module is intentionally deterministic. It does not invent arbitrary source
code. It checks common Brain failure modes and runs only explicit, local repair
actions. More advanced code synthesis can be plugged in through
BRAIN_REPAIR_COMMAND after review.
"""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    # Keep the built-in repair safe: no network, no secret discovery, no force-push.
    actions = os.getenv("BRAIN_REPAIR_ACTIONS", "").strip()
    if not actions:
        print("REPAIR_NO_BUILTIN_ACTIONS")
        return 0

    allowed = {
        "compile": [sys.executable, "-m", "compileall", "-q", "brain_v12"],
        "tests": [sys.executable, "-m", "pytest", "-q"],
    }
    for name in [x.strip() for x in actions.split(",") if x.strip()]:
        if name not in allowed:
            print(f"REPAIR_ACTION_NOT_ALLOWED={name}", file=sys.stderr)
            return 2
        p = subprocess.run(allowed[name], text=True, capture_output=True)
        print(p.stdout[-6000:])
        print(p.stderr[-6000:], file=sys.stderr)
        if p.returncode != 0:
            return p.returncode

    print("REPAIR_DISPATCH=SUCCESS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

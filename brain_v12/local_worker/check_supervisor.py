#!/usr/bin/env python3
"""Inspect local Brain worker supervisor health."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "brain6_artifacts" / "local_worker" / "supervisor.json"

def main():
    if not STATE.exists():
        print(json.dumps({"status": "DOWN", "reason": "no_supervisor_state"}, indent=2))
        return 1
    data = json.loads(STATE.read_text(encoding="utf-8"))
    ok = data.get("status") == "READY"
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

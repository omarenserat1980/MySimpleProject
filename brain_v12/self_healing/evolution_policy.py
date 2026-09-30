#!/usr/bin/env python3
"""Brain evolution policy: never accept an unverified rewrite.

This module is used by continuous review loops to make the rule explicit:
inspect -> propose -> apply -> verify -> retain only verified state.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"


def snapshot(label: str) -> dict:
    p = subprocess.run(["git", "diff", "--binary"], cwd=ROOT,
                       text=True, capture_output=True)
    return {"label": label, "diff": p.stdout[-50000:]}


def record(event: dict) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "evolution_events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def require_verified(ok: bool, label: str) -> None:
    if not ok:
        record({"event": "REJECT_UNVERIFIED_REWRITE", "label": label})
        raise RuntimeError("Brain rejected an unverified code rewrite")


def review_roots() -> list[str]:
    roots = os.getenv("BRAIN_REVIEW_ROOTS", "brain_v12,tests,scripts")
    return [x.strip() for x in roots.split(",") if x.strip()]

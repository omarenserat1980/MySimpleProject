#!/usr/bin/env python3
"""Deterministic Brain 6 preflight/repair gate.

This tool does not rewrite source code automatically. It validates the campaign
contract and creates a machine-readable report so the workflow can fail early
with a precise reason instead of wasting a long runner allocation.
"""
from __future__ import annotations

import json
import os
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "production" / "BRAIN6_168H.json"
REPORT = ROOT / "brain6_preflight_report.json"

required = [
    ROOT / ".github" / "workflows" / "brain6-168h-cloud.yml",
    ROOT / "brain6_cpp" / "main.cpp",
    ROOT / "brain6_cs" / "Program.cs",
    ROOT / "brain6_cs" / "Brain6.csproj",
]

errors: list[str] = []
checks: list[str] = []

for path in required:
    if path.is_file() and path.stat().st_size > 0:
        checks.append(f"present:{path.relative_to(ROOT)}")
    else:
        errors.append(f"missing_or_empty:{path.relative_to(ROOT)}")

try:
    state = json.loads(STATE.read_text(encoding="utf-8"))
except Exception as exc:
    state = {}
    errors.append(f"invalid_state_json:{exc}")

if state.get("enabled") is not True:
    errors.append("campaign_disabled")
if state.get("campaign") != "BRAIN6_168H":
    errors.append("wrong_campaign")
if state.get("duration_seconds") != 604800:
    errors.append("duration_must_be_604800")
if state.get("free_only") is not True:
    errors.append("free_only_must_be_true")
if state.get("youtube_publish") is not False:
    errors.append("youtube_publish_must_be_false")

try:
    started = float(state["started_epoch"])
    elapsed = max(0.0, time.time() - started)
    remaining = max(0.0, 604800.0 - elapsed)
    checks.append(f"campaign_remaining_seconds={remaining:.0f}")
except Exception as exc:
    remaining = 0.0
    errors.append(f"invalid_started_epoch:{exc}")

# A completed campaign is a clean terminal state, not a failed workflow.
complete = remaining <= 0 and not errors

report = {
    "version": 1,
    "status": "COMPLETE" if complete else ("READY" if not errors else "BLOCKED"),
    "checks": checks,
    "errors": errors,
    "remaining_seconds": round(remaining),
    "timestamp_epoch": int(time.time()),
}

REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))

if errors:
    raise SystemExit(2)

#!/usr/bin/env python3
"""Bridge Brain runtime events into the V12 causal evidence ledger.

This module is deliberately conservative. It does not discover universal
causality from correlation. It records operational evidence from the Brain
control-plane event stream: an action/attempt followed by a terminal outcome
for the same job is evidence about that workflow path.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

from brain_v12.causal.causal_engine import CausalEvidenceLedger

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".brain" / "state"
LEDGER = STATE / "causal_evidence.json"


def resolve_events_path() -> Path:
    """Resolve the authoritative event stream used by BrainSupervisor.

    BRAIN_RUNTIME_HOME is authoritative when configured. Otherwise prefer the
    persistent supervisor/control-plane stream, while retaining the legacy
    repository-local path for standalone CI/control-plane runs.
    """
    configured_home = os.environ.get("BRAIN_RUNTIME_HOME")
    if configured_home:
        return (
            Path(configured_home).expanduser()
            / "brain6_artifacts"
            / "supervisor"
            / "control_plane"
            / "events.jsonl"
        )

    runtime_events = (
        Path("~/.brain/runtime").expanduser()
        / "brain6_artifacts"
        / "supervisor"
        / "control_plane"
        / "events.jsonl"
    )
    legacy_events = ROOT / "brain6_artifacts" / "control_plane" / "events.jsonl"

    # Prefer a populated source over an empty stale file; never merge streams
    # from different runtime roots into one evidence report.
    if runtime_events.exists() and runtime_events.stat().st_size > 0:
        return runtime_events
    if legacy_events.exists() and legacy_events.stat().st_size > 0:
        return legacy_events
    if runtime_events.exists():
        return runtime_events
    return legacy_events


# Compatibility alias for callers that imported the former module constant.
EVENTS = resolve_events_path()


def read_events(path: Optional[Path] = None) -> List[dict]:
    events_path = path or resolve_events_path()
    if not events_path.exists():
        return []
    rows = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows


def build_ledger(events: List[dict]) -> CausalEvidenceLedger:
    ledger = CausalEvidenceLedger()
    by_job: Dict[str, List[dict]] = {}
    for event in events:
        job_id = str(event.get("job_id", ""))
        if job_id:
            by_job.setdefault(job_id, []).append(event)

    for job_events in by_job.values():
        started = any(e.get("event") == "attempt_started" for e in job_events)
        completed = any(e.get("event") == "checkpoint" and
                        isinstance(e.get("data"), dict) and
                        e["data"].get("step_index") is not None
                        for e in job_events)
        blocked = any(e.get("event") == "blocked" for e in job_events)

        if started and completed:
            ledger.record("attempt_started", "checkpoint", success=True,
                          source="brain_control_plane")
        if started and blocked:
            ledger.record("attempt_started", "blocked", success=False,
                          source="brain_control_plane")

    return ledger


def build_report(events: List[dict], source: str = "") -> dict:
    """Return an explicit evidence state; an empty stream is not recorded proof."""
    ledger = build_ledger(events)
    records = ledger.snapshot()
    status = "RECORDED" if events and records else "NO_RUNTIME_EVIDENCE"
    return {
        "schema": "brain-causal-evidence/v1",
        "created_at": time.time(),
        "source": source,
        "event_count": len(events),
        "record_count": len(records),
        "status": status,
        "records": records,
    }


def main() -> int:
    events_path = resolve_events_path()
    events = read_events(events_path)
    report = build_report(events, str(events_path))
    STATE.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "CAUSAL_EVIDENCE": report["status"],
        "events": report["event_count"],
        "records": report["record_count"],
        "source": report["source"],
        "evidence_file": str(LEDGER),
    }, ensure_ascii=False))
    # Evidence absence is reported explicitly, but does not turn this
    # collection step into a hard failure for simulation-only CI runs.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

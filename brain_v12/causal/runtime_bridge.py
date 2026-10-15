#!/usr/bin/env python3
"""Bridge Brain runtime events into the V12 causal evidence ledger.

This module is deliberately conservative. It does not discover universal
causality from correlation. It records operational evidence from the Brain
control-plane event stream: an action/attempt followed by a terminal outcome
for the same job is evidence about that workflow path.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

from brain_v12.causal.causal_engine import CausalEvidenceLedger

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "brain6_artifacts" / "control_plane" / "events.jsonl"
STATE = ROOT / ".brain" / "state"
LEDGER = STATE / "causal_evidence.json"


def read_events() -> List[dict]:
    if not EVENTS.exists():
        return []
    rows = []
    for line in EVENTS.read_text(encoding="utf-8").splitlines():
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
    events = read_events()
    report = build_report(events, str(EVENTS))
    STATE.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "CAUSAL_EVIDENCE": report["status"],
        "events": report["event_count"],
        "records": report["record_count"],
        "evidence_file": str(LEDGER),
    }, ensure_ascii=False))
    # Evidence absence is reported explicitly, but does not turn this
    # collection step into a hard failure for simulation-only CI runs.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

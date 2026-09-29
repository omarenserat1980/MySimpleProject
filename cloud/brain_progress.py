"""Persistent Brain progress ledger.

Only verified evidence advances the development counters.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"STATE"/"brain_commands"
LEDGER=STATE/"progress.json"

def update_progress(result: dict[str,Any]) -> dict[str,Any]:
    STATE.mkdir(parents=True,exist_ok=True)
    current={"commands_issued":0,"verified_results":0,"failed_or_blocked":0,"evidence_items":0,"last_update":None}
    if LEDGER.exists():
        current.update(json.loads(LEDGER.read_text(encoding="utf-8")))
    current["commands_issued"] += 1
    status=result.get("status")
    if status=="VERIFIED":
        current["verified_results"] += 1
        current["evidence_items"] += len(result.get("evidence",[]))
    elif status in {"FAILED","BLOCKED"}:
        current["failed_or_blocked"] += 1
    current["last_update"]=datetime.now(timezone.utc).isoformat()
    LEDGER.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding="utf-8")
    return current

if __name__=="__main__":
    latest=STATE/"latest.json"
    if not latest.exists():
        raise SystemExit("No Brain command result exists")
    print(json.dumps(update_progress(json.loads(latest.read_text(encoding="utf-8"))),ensure_ascii=False,indent=2))

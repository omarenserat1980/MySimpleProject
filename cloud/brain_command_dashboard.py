"""Validate and classify Brain command results for the visible progress stream."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"STATE"/"brain_commands"

def dashboard() -> dict[str, Any]:
    latest=STATE/"latest.json"
    if not latest.exists():
        return {"status":"NO_COMMAND","commands":[]}
    data=json.loads(latest.read_text(encoding="utf-8"))
    return {
        "status": data.get("status","UNKNOWN"),
        "command_id": data.get("command_id"),
        "intent": data.get("intent"),
        "task": data.get("task"),
        "reason": data.get("reason"),
        "evidence_required": data.get("evidence_required",[]),
        "result_summary": data.get("result_summary"),
        "evidence": data.get("evidence",[]),
        "next": "await_executor_result" if data.get("status")=="REQUESTED" else "issue_next_command",
    }

if __name__=="__main__":
    print(json.dumps(dashboard(),ensure_ascii=False,indent=2))

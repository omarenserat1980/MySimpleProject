"""Brain command stream and executor bridge.

Creates a deterministic first command from Brain's known blockers and records
an execution lifecycle. Actual external execution remains subject to the
connected executor's authorization; this module never runs arbitrary commands.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cloud.brain_command_protocol import issue_command, latest_command

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "STATE" / "brain_commands"

def create_next_command() -> dict[str, Any]:
    command = issue_command(
        intent="inspect",
        task="Inspect the current Brain cinematic production blockers, self-healing evidence, and benchmark readiness; return concrete next actions.",
        reason="Brain's operational interview identifies evidence, benchmark execution, self-correction, sensory verification, and observability as critical needs.",
        evidence_required=[
            "current Brain interview report",
            "self-healing state",
            "cinematic reliability tests",
            "benchmark registry status",
        ],
        priority="high",
    )
    return command

def record_result(command_id: str, status: str, summary: str, evidence: list[str]) -> dict[str, Any]:
    allowed = {"EXECUTED", "VERIFIED", "BLOCKED", "FAILED"}
    if status not in allowed:
        raise ValueError("invalid command result status")
    path = STATE / f"{command_id}.json"
    if not path.exists():
        raise FileNotFoundError(command_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update({"status": status, "result_summary": summary, "evidence": evidence})
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (STATE / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

if __name__ == "__main__":
    print(json.dumps(create_next_command(), ensure_ascii=False, indent=2))

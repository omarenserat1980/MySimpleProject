"""Brain command loop: issue -> observe result -> decide next command."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from cloud.brain_command_protocol import issue_command

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"STATE"/"brain_commands"

def next_from_result(result: dict[str, Any]) -> dict[str, Any]:
    status=result.get("status")
    if status=="VERIFIED":
        return issue_command(
            "verify",
            "Verify the claimed improvement against the required evidence and compare it with the previous verified state.",
            "A previous Brain command produced a verified result; the next step is independent verification.",
            ["previous command result","verification output","comparison with prior state"],
            "high",
        )
    if status in {"FAILED","BLOCKED"}:
        return issue_command(
            "inspect",
            "Inspect the failure or block, identify the smallest supported repair, and return a bounded repair request.",
            "The previous Brain command did not reach verified state.",
            ["failure evidence","root-cause evidence","bounded repair proposal"],
            "high",
        )
    return issue_command(
        "report",
        "Report the current command state and wait for executor evidence; do not claim completion.",
        "The previous command has not produced verified evidence yet.",
        ["executor result","evidence status"],
        "normal",
    )

def main() -> dict[str,Any]:
    latest=STATE/"latest.json"
    if not latest.exists():
        return issue_command(
            "inspect",
            "Inspect Brain's current blockers and production readiness.",
            "No command result exists yet.",
            ["Brain interview","self-healing state","benchmark readiness"],
            "high",
        )
    result=json.loads(latest.read_text(encoding="utf-8"))
    return next_from_result(result)

if __name__=="__main__":
    print(json.dumps(main(),ensure_ascii=False,indent=2))

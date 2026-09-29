"""Evidence-driven Self-Healing Loop for Brain Cloud.

The loop converts Brain's operational interview into bounded repair actions.
It may run only allow-listed deterministic repair/test commands; unknown
failures become BLOCKED rather than triggering arbitrary code changes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from cloud.brain_interview import conduct_interview

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "STATE" / "self_healing"


@dataclass(frozen=True)
class RepairAction:
    key: str
    reason: str
    command: tuple[str, ...]
    evidence: tuple[str, ...]


ALLOWLIST = {
    "stage7": RepairAction(
        "stage7",
        "cinematic self-healing gate",
        (sys.executable, "brain_v12/movie_summary_factory/room13_stage7_repair.py"),
        ("Stage 7 repair output",),
    ),
    "interview_tests": RepairAction(
        "interview_tests",
        "validate Brain interview contract",
        (sys.executable, "-m", "unittest", "cloud.test_brain_interview"),
        ("interview test result",),
    ),
    "film_reliability_tests": RepairAction(
        "film_reliability_tests",
        "validate cinematic reliability contract",
        (sys.executable, "-m", "unittest", "cloud.test_film_reliability"),
        ("reliability test result",),
    ),
}


def _actions_for(report: dict[str, Any]) -> list[RepairAction]:
    blockers = set(report.get("blockers", []))
    actions = [ALLOWLIST["interview_tests"]]
    if "cinematic_shot_manifest_may_be_missing_for_strict_sensory_qc" in blockers:
        actions.append(ALLOWLIST["stage7"])
        actions.append(ALLOWLIST["film_reliability_tests"])
    return actions


def run_loop() -> dict[str, Any]:
    report = conduct_interview()
    actions = _actions_for(report)
    results: list[dict[str, Any]] = []

    for action in actions:
        proc = subprocess.run(
            list(action.command),
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
        results.append({
            **asdict(action),
            "command": list(action.command),
            "return_code": proc.returncode,
            "status": "PASS" if proc.returncode == 0 else "BLOCKED",
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        })
        if proc.returncode != 0:
            break

    overall = "HEALED_AND_VERIFIED" if results and all(r["status"] == "PASS" for r in results) else "BLOCKED"
    output = {
        "status": overall,
        "loop": "interview -> needs -> allowlisted repair/test -> evidence",
        "interview": report,
        "actions": results,
        "arbitrary_code_execution": False,
        "unknown_failures_are_blocked": True,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "latest.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output


if __name__ == "__main__":
    print(json.dumps(run_loop(), ensure_ascii=False, indent=2))

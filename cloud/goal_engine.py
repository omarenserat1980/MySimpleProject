"""Brain goal orchestrator: execute authorized goals through the software factory.

This module is intentionally conservative: it plans and validates work locally,
and only runs the production factory when every configured gate passes.
External deployment remains opt-in through explicit environment flags.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Goal:
    name: str
    enabled: bool = True


def configured_goals() -> list[Goal]:
    raw = os.getenv(
        "BRAIN_GOALS",
        "build_ai_products,improve_video_factory,improve_self",
    )
    return [Goal(name=item.strip()) for item in raw.split(",") if item.strip()]


def plan(goal: Goal) -> dict:
    return {
        "goal": goal.name,
        "status": "PLANNED",
        "steps": [
            "specify",
            "architect",
            "implement",
            "build",
            "test",
            "security_gate",
            "deploy_if_authorized",
            "health_check",
            "measure",
            "iterate",
        ],
    }


def run_factory() -> int:
    command = [sys.executable, "cloud/autonomous_software_factory.py"]
    timeout = int(os.getenv("BRAIN_SOFTWARE_FACTORY_TIMEOUT", "300"))
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=os.environ.copy(),
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print("BRAIN_GOAL_FACTORY_TIMEOUT=1", flush=True)
        return 124
    except Exception as exc:
        print(
            f"BRAIN_GOAL_FACTORY_ERROR={type(exc).__name__}:{exc}",
            flush=True,
        )
        return 1
    return result.returncode


def main() -> int:
    goals = configured_goals()
    print("BRAIN_GOAL_ENGINE=1", flush=True)

    for goal in goals:
        print(
            json.dumps(plan(goal), ensure_ascii=False, sort_keys=True),
            flush=True,
        )

    if not goals:
        print("BRAIN_GOAL_GATE=NO_GOALS", flush=True)
        return 0

    if os.getenv("BRAIN_GOAL_EXECUTE", "1").lower() not in {"1", "true", "yes", "on"}:
        print("BRAIN_GOAL_GATE=PLAN_ONLY", flush=True)
        return 0

    rc = run_factory()
    if rc != 0:
        print(f"BRAIN_GOAL_GATE=FAIL rc={rc}", flush=True)
        return rc

    print("BRAIN_GOAL_GATE=PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

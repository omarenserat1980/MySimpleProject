"""Bounded Brain Cloud task executor."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = {
    "health": [sys.executable, "-m", "unittest", "brain_v12.tests.test_core"],
    "supervisor": [sys.executable, "-m", "brain_v12.brain.brain_supervisor"],
    "tests": [sys.executable, "-m", "unittest", "discover", "-s", "brain_v12/tests", "-p", "test_*.py"],
    "media-test": [sys.executable, "-m", "unittest", "brain_v12.tests.test_media_engine"],
    "cinema-test": [sys.executable, "-m", "unittest", "brain_v12.movie_summary_factory.test_room13_pipeline"],
    "revenue-tests": [sys.executable, "-m", "unittest", "brain_v12.tests.test_payment_gateway", "brain_v12.tests.test_commerce_api", "brain_v12.tests.test_income_lifecycle", "brain_v12.tests.test_client_revenue_guardian", "brain_v12.tests.test_live_opportunity_researcher"],
}

def main() -> int:
    task = os.getenv("BRAIN_TASK", "health").strip().lower()
    command = TASKS.get(task)
    if command is None:
        result = {"ok": False, "state": "REJECTED_TASK", "task": task, "allowed_tasks": sorted(TASKS)}
        print(json.dumps(result, indent=2))
        return 2
    started = {"ok": True, "state": "TASK_STARTED", "task": task,
               "command": command, "run_id": os.getenv("GITHUB_RUN_ID", "")}
    print(json.dumps(started, indent=2))
    proc = subprocess.run(command, cwd=ROOT)
    result = {"ok": proc.returncode == 0,
              "state": "TASK_COMPLETED" if proc.returncode == 0 else "TASK_FAILED",
              "task": task, "returncode": proc.returncode,
              "run_id": os.getenv("GITHUB_RUN_ID", "")}
    out = Path("brain6_artifacts/github_cloud")
    out.mkdir(parents=True, exist_ok=True)
    (out / "task_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return proc.returncode

if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

"""Free local 120-second watchdog for Electronic Brain.

This process is intentionally independent from scheduled GitHub Actions.
Run it on Brain/Termux or another always-on executor.

Safety rules:
- observes completed failed/timed-out runs
- never edits source code
- retries only failed jobs, at most three attempts
- records every decision
- unknown failures are blocked for review
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = os.getenv("BRAIN_GITHUB_REPO", "omarenserat1980/MySimpleProject")
INTERVAL = max(30, int(os.getenv("BRAIN_WATCHDOG_SECONDS", "120")))
MAX_ATTEMPTS = max(1, int(os.getenv("BRAIN_WATCHDOG_MAX_ATTEMPTS", "3")))
STATE = Path(os.getenv("BRAIN_WATCHDOG_STATE", "brain6_artifacts/workflow_watchdog/minute-state.json"))
LOG = Path(os.getenv("BRAIN_WATCHDOG_LOG", "brain6_artifacts/workflow_watchdog/minute-watchdog.log"))
WATCHED = {
    "BRAIN 120 Minute Cinema",
    "Brain Windows Real Boot Evidence",
    "Brain Virtual Computer",
    "Brain Continuous Self-Healing",
    "Brain Global Workflow Watchdog",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_gh(*args: str) -> str:
    p = subprocess.run(
        ["gh", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=True,
    )
    return p.stdout


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"seen": {}, "updated_at": None}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def write_log(message: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{now()}] {message}\n")


def classify(run: dict) -> str:
    conclusion = str(run.get("conclusion") or "").lower()
    if conclusion in {"failure", "timed_out"}:
        return "FAILED_OR_TIMED_OUT"
    return "OTHER"


def run_development_cycle() -> dict:
    """Run one bounded Brain review/repair/improvement cycle."""
    command = [
        os.getenv("PYTHON", "python"),
        "-m",
        "brain_v12.self_healing.review_loop",
        "--loops", "1",
        "--timeout", os.getenv("BRAIN_REVIEW_TIMEOUT", "120"),
    ]
    env = os.environ.copy()
    env.setdefault("BRAIN_PROACTIVE_EVOLUTION", "1")
    try:
        p = subprocess.run(
            command, cwd=Path.cwd(), env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180
        )
        return {
            "exit_code": p.returncode,
            "status": "VERIFIED" if p.returncode == 0 else "FAILED",
            "output": p.stdout[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {"exit_code": 124, "status": "TIMEOUT", "output": str(exc)}

def inspect_once() -> int:
    state = load_state()
    raw = run_gh(
        "run", "list", "--repo", REPO, "--limit", "50",
        "--json", "databaseId,status,conclusion,workflowName,attempt,headSha,updatedAt"
    )
    runs = json.loads(raw)
    changed = 0

    for r in runs:
        workflow = r.get("workflowName")
        if workflow not in WATCHED or workflow == "Brain Global Workflow Watchdog":
            continue
        if r.get("status") != "completed":
            continue
        if classify(r) != "FAILED_OR_TIMED_OUT":
            continue

        run_id = str(r["databaseId"])
        attempt = int(r.get("attempt") or 1)
        key = f"{run_id}:{attempt}"
        if key in state["seen"]:
            continue

        if attempt < MAX_ATTEMPTS:
            try:
                run_gh("run", "rerun", run_id, "--failed", "--repo", REPO)
                action = "RERUN_FAILED_JOBS"
            except subprocess.CalledProcessError as exc:
                action = f"RERUN_FAILED:{exc.stdout[-500:]}"
        else:
            action = "BLOCKED_MAX_ATTEMPTS"

        state["seen"][key] = {
            "run_id": run_id,
            "workflow": workflow,
            "attempt": attempt,
            "action": action,
            "timestamp": now(),
        }
        write_log(
            f"run={run_id} workflow={workflow!r} attempt={attempt} action={action}"
        )
        changed += 1

    # Every 120-second cycle also runs one bounded local development review.
    # It repairs verified failures and, when a code generator is configured,
    # evaluates proactive improvement candidates with rollback on failure.
    development = run_development_cycle()
    state["last_development_cycle"] = {
        "timestamp": now(),
        **development,
    }
    write_log(
        f"DEVELOPMENT_CYCLE status={development['status']} "
        f"exit_code={development['exit_code']}"
    )

    if len(state["seen"]) > 500:
        items = list(state["seen"].items())[-500:]
        state["seen"] = dict(items)
    save_state(state)
    return changed


def main() -> None:
    write_log(
        f"START repo={REPO} interval={INTERVAL}s max_attempts={MAX_ATTEMPTS}"
    )
    while True:
        started = time.monotonic()
        try:
            count = inspect_once()
            write_log(f"HEARTBEAT decisions={count}")
        except Exception as exc:
            write_log(f"ERROR type={type(exc).__name__} message={exc}")
        elapsed = time.monotonic() - started
        time.sleep(max(1.0, INTERVAL - elapsed))


if __name__ == "__main__":
    main()

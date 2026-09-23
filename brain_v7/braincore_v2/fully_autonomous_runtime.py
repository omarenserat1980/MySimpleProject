"""Continuous autonomous runtime for Brain V7.

Runs cognitive/economic cycles continuously, generates fresh goals, checkpoints
state, and supports an emergency stop. Optional self-start mode can relaunch
the runtime after recoverable process exits when an external supervisor invokes
the entrypoint. External irreversible side effects remain permission-gated.
"""
from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path
from dataclasses import dataclass, asdict

from .health_monitor import check as health_check
from .continuous_goal_engine import next_goal
from .worker_health import WorkerHealthRegistry


@dataclass
class RuntimeState:
    cycle: int = 0
    status: str = "STOPPED"
    current_goal_id: str = ""
    current_goal: str = ""
    last_result: str = ""
    last_error: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0
    restart_count: int = 0


class AutonomousRuntime:
    def __init__(self, state_path: str = "brain_runtime_state.json",
                 stop_path: str = "STOP_BRAIN",
                 sleep_seconds: int | None = None):
        self.state_path = Path(state_path)
        self.stop_path = Path(stop_path)
        self.sleep_seconds = max(
            1, int(sleep_seconds if sleep_seconds is not None
                   else os.getenv("BRAIN_SLEEP_SECONDS", "60"))
        )
        self.state = self._load()
        self.health = WorkerHealthRegistry(stale_after_s=180)
        self.worker_id = os.getenv("WORKER_ID", "brain-v7-core")

    def _load(self) -> RuntimeState:
        try:
            data = json.loads(self.state_path.read_text())
            return RuntimeState(**data)
        except Exception:
            return RuntimeState()

    def _save(self) -> None:
        self.state.updated_at = time.time()
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.state), ensure_ascii=False, indent=2))
        tmp.replace(self.state_path)

    def stop_requested(self) -> bool:
        return self.stop_path.exists() or os.getenv("STOP_BRAIN", "").lower() in {
            "1", "true", "yes"
        }

    def _heartbeat(self, status: str, detail: str = "") -> None:
        beat = self.health.beat(self.worker_id, status=status, cycle=self.state.cycle, detail=detail)
        print(json.dumps({"event": "WORKER_HEARTBEAT", **beat}, ensure_ascii=False), flush=True)

    def run_cycle(self) -> dict:
        self._heartbeat("HEALTHY", "cycle_start")
        if self.stop_requested():
            self.state.status = "STOP_REQUESTED"
            self._save()
            return {"status": self.state.status}

        health = health_check()
        if not health.get("healthy", False):
            self.state.status = "HEALTH_BLOCKED"
            self._save()
            return {"status": self.state.status, "health": health}

        self.state.cycle += 1
        goal = next_goal(self.state.cycle)
        self.state.current_goal_id = goal.goal_id
        self.state.current_goal = goal.title
        self.state.status = "RUNNING"
        self._save()

        try:
            # Lazy-load the task engine so a single module/import regression is
            # reported as a recoverable runtime error instead of killing Render.
            from .autonomous_task import run as run_task
            objective = (
                "نفّذ الهدف الحالي بأقل وقت وبطريقة مشروعة: "
                + goal.title
                + ". طوّر قدرات الدماغ ونفّذ داخليًا ما يمكن تنفيذه."
            )
            result = run_task(objective, max_steps=12)
            self.state.last_result = str(result)[-4000:]
            self.state.last_error = ""
            self.state.status = "CYCLE_COMPLETE"
            self._save()
            self._heartbeat("HEALTHY", "cycle_complete")
            return {
                "status": self.state.status,
                "cycle": self.state.cycle,
                "goal": asdict(goal),
                "result": result,
            }
        except Exception as exc:
            self.state.last_error = repr(exc)
            self.state.status = "RECOVERABLE_ERROR"
            self._save()
            self._heartbeat("ERROR", repr(exc))
            return {"status": self.state.status, "error": repr(exc)}

    def run_forever(self) -> None:
        self.state.started_at = self.state.started_at or time.time()
        self.state.status = "RUNNING"
        self._save()

        while not self.stop_requested():
            try:
                self.run_cycle()
            except Exception as exc:
                self.state.last_error = repr(exc)
                self.state.status = "RECOVERABLE_ERROR"
                self._save()
                self._heartbeat("ERROR", repr(exc))
                # Keep the Render worker alive long enough for the next cycle
                # to retry after transient imports, network failures, or I/O errors.
                if not self.stop_requested():
                    time.sleep(min(max(self.sleep_seconds, 5), 120))
            if not self.stop_requested():
                time.sleep(self.sleep_seconds)

        self.state.status = "STOPPED"
        self._save()


def run_forever() -> None:
    """Main long-running entrypoint for a cloud/PC/Termux supervisor."""
    AutonomousRuntime().run_forever()

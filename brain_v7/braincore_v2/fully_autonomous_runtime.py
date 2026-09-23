"""Continuous autonomous runtime for Brain V7.

Runs the internal cognitive/economic loop continuously with bounded cycles,
health checks, checkpointing, recovery, and an emergency stop file.

It can autonomously research, plan, create, validate, package and learn.
External irreversible side effects remain permission-gated by the existing
governance/payment layers; this module never bypasses them.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from dataclasses import dataclass, asdict

from .autonomous_task import run as run_task
from .health_monitor import check as health_check


@dataclass
class RuntimeState:
    cycle: int = 0
    status: str = "STOPPED"
    last_result: str = ""
    last_error: str = ""
    started_at: float = 0.0
    updated_at: float = 0.0


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

    def _load(self) -> RuntimeState:
        try:
            return RuntimeState(**json.loads(self.state_path.read_text()))
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

    def run_cycle(self) -> dict:
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
        self.state.status = "RUNNING"
        self._save()

        try:
            result = run_task(
                "طوّر قدرات الدماغ واكتشف ونفّذ داخليًا فرص ربح مشروعة قابلة للإثبات",
                max_steps=12,
            )
            self.state.last_result = str(result)[-4000:]
            self.state.last_error = ""
            self.state.status = "CYCLE_COMPLETE"
            self._save()
            return {"status": self.state.status, "cycle": self.state.cycle,
                    "result": result}
        except Exception as exc:
            self.state.last_error = repr(exc)
            self.state.status = "RECOVERABLE_ERROR"
            self._save()
            return {"status": self.state.status, "error": repr(exc)}

    def run_forever(self) -> None:
        self.state.started_at = self.state.started_at or time.time()
        self.state.status = "RUNNING"
        self._save()

        while not self.stop_requested():
            self.run_cycle()
            if not self.stop_requested():
                time.sleep(self.sleep_seconds)

        self.state.status = "STOPPED"
        self._save()


def run_forever() -> None:
    AutonomousRuntime().run_forever()

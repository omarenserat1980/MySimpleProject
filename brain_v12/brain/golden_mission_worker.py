"""Opt-in background reminder loop for due Golden Missions.

This worker sends status reminders only. It never executes mission objectives.
"""
from __future__ import annotations

import os
import threading
from typing import Any


class GoldenMissionReminderWorker:
    def __init__(self, controller, interval_seconds: int | None = None):
        self.controller = controller
        self.interval_seconds = max(30, int(interval_seconds or os.getenv("BRAIN_GOLDEN_MISSION_POLL_SECONDS", "300")))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def tick(self) -> dict[str, Any]:
        return self.controller.notify_due()

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="brain-golden-mission-reminders", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                # A reminder failure must not take down the Brain API.
                pass
            self._stop.wait(self.interval_seconds)

"""Opt-in background reminder loop for due Golden Missions.

This worker sends status reminders only. It never executes mission objectives.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any


class GoldenMissionReminderWorker:
    def __init__(self, controller, interval_seconds: int | None = None):
        self.controller = controller
        self.interval_seconds = max(30, int(interval_seconds or os.getenv("BRAIN_GOLDEN_MISSION_POLL_SECONDS", "300")))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._started_at: str | None = None
        self._last_tick_at: str | None = None
        self._last_result: dict[str, Any] | None = None
        self._last_error: str | None = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def status(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "running": bool(self._thread and self._thread.is_alive() and not self._stop.is_set()),
                "interval_seconds": self.interval_seconds,
                "started_at": self._started_at,
                "last_tick_at": self._last_tick_at,
                "last_result": dict(self._last_result) if self._last_result is not None else None,
                "last_error": self._last_error,
                "mode": "REMINDERS_ONLY",
            }

    def tick(self) -> dict[str, Any]:
        try:
            result = self.controller.notify_due()
        except Exception as exc:
            with self._state_lock:
                self._last_tick_at = self._now()
                self._last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
            raise
        with self._state_lock:
            self._last_tick_at = self._now()
            self._last_result = dict(result) if isinstance(result, dict) else {"result": str(result)[:500]}
            self._last_error = None
        return result

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return False
        self._stop.clear()
        with self._state_lock:
            self._started_at = self._now()
            self._last_error = None
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

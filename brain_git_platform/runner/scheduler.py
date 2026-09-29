from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


@dataclass
class Run:
    workflow: str
    repository: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str | None = None


class BrainRunnerScheduler:
    """Thread-safe queue with a managed worker loop."""

    def __init__(self):
        self._queue: queue.Queue[str] = queue.Queue()
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None

    def enqueue(self, repository: str, workflow: str) -> Run:
        run = Run(workflow=workflow, repository=repository)
        with self._lock:
            self._runs[run.id] = run
        self._queue.put(run.id)
        return run

    def claim(self) -> Run | None:
        try:
            run_id = self._queue.get_nowait()
        except queue.Empty:
            return None
        with self._lock:
            run = self._runs[run_id]
            run.status = "running"
            return run

    def complete(self, run_id: str, success: bool, error: str | None = None) -> Run:
        with self._lock:
            run = self._runs[run_id]
            run.status = "success" if success else "failure"
            run.error = error
            return run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def start(self, handler: Callable[[Run], bool]) -> None:
        if self._worker and self._worker.is_alive():
            return

        def loop():
            while not self._stop.is_set():
                try:
                    run_id = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                with self._lock:
                    run = self._runs[run_id]
                    run.status = "running"
                try:
                    ok = bool(handler(run))
                    self.complete(run_id, ok)
                except Exception as exc:
                    self.complete(run_id, False, str(exc))
                finally:
                    self._queue.task_done()

        self._stop.clear()
        self._worker = threading.Thread(target=loop, name="brain-runner", daemon=True)
        self._worker.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._worker:
            self._worker.join(timeout=timeout)
        self._worker = None

from __future__ import annotations
import queue, threading, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class Run:
    workflow: str
    repository: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BrainRunnerScheduler:
    """In-process scheduler contract; production workers can consume the same queue."""
    def __init__(self):
        self._queue = queue.Queue()
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

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

    def complete(self, run_id: str, success: bool) -> Run:
        with self._lock:
            run = self._runs[run_id]
            run.status = "success" if success else "failure"
            return run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

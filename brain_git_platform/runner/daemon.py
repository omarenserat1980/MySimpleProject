from __future__ import annotations

import threading
import uuid
from pathlib import Path

from .worker import worker_once


class BrainRunnerDaemon:
    """Long-lived Brain-native worker backed by the durable SQLite queue."""

    def __init__(self, root: Path):
        self.root = root
        self.worker_id = "daemon-" + uuid.uuid4().hex
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            result = worker_once(self.worker_id)
            if result is None:
                self._stop.wait(0.5)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="brain-native-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._thread = None

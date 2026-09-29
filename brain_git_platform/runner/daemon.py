from __future__ import annotations

import threading
import uuid
from pathlib import Path

from .worker import worker_once


class BrainRunnerDaemon:
    """Long-lived Brain-native worker pool backed by the durable SQLite queue."""

    def __init__(self, root: Path, workers: int = 1):
        if workers < 1 or workers > 64:
            raise ValueError("workers must be between 1 and 64")
        self.root = root
        self.worker_count = workers
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def _loop(self, worker_id: str) -> None:
        while not self._stop.is_set():
            result = worker_once(worker_id)
            if result is None:
                self._stop.wait(0.5)

    def start(self) -> None:
        if any(thread.is_alive() for thread in self._threads):
            return
        self._stop.clear()
        self._threads = []
        for _ in range(self.worker_count):
            worker_id = "daemon-" + uuid.uuid4().hex
            thread = threading.Thread(
                target=self._loop,
                args=(worker_id,),
                name=f"brain-native-worker-{worker_id[-6:]}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=timeout)
        self._threads = []

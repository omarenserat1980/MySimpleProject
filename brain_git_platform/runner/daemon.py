from __future__ import annotations

from pathlib import Path

from .scheduler import BrainRunnerScheduler, Run
from .worker import execute_queued_run


class BrainRunnerDaemon:
    """Long-lived Brain-native scheduler/worker adapter."""

    def __init__(self, root: Path):
        self.root = root
        self.scheduler = BrainRunnerScheduler()

    def _handle(self, run: Run) -> bool:
        # The durable workflow database remains the source of truth.
        execute_queued_run(int(run.id))
        return True

    def start(self) -> None:
        self.scheduler.start(self._handle)

    def stop(self) -> None:
        self.scheduler.stop()

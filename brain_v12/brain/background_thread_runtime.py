from __future__ import annotations

"""Brain-owned bounded background thread runtime.

This is infrastructure, not an authority bypass. Background jobs must call the
same Brain gateways/contracts used by foreground execution. The supervisor
owns lifecycle, duplicate prevention, crash recovery, exponential backoff,
health snapshots, and graceful shutdown.
"""

from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Callable
import time
import traceback


JobFn = Callable[[Event], None]


@dataclass(frozen=True)
class BackgroundJobSpec:
    name: str
    target: JobFn
    interval_seconds: float = 5.0
    initial_delay_seconds: float = 0.0
    max_backoff_seconds: float = 300.0
    restart_on_failure: bool = True

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("BACKGROUND_JOB_NAME_REQUIRED")
        if self.interval_seconds <= 0:
            raise ValueError("BACKGROUND_JOB_INTERVAL_INVALID")
        if self.initial_delay_seconds < 0:
            raise ValueError("BACKGROUND_JOB_INITIAL_DELAY_INVALID")
        if self.max_backoff_seconds < self.interval_seconds:
            raise ValueError("BACKGROUND_JOB_MAX_BACKOFF_INVALID")


@dataclass
class BackgroundJobState:
    name: str
    state: str = "REGISTERED"
    started_at: float | None = None
    last_started_at: float | None = None
    last_finished_at: float | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    restart_count: int = 0
    run_count: int = 0


@dataclass
class _RuntimeJob:
    spec: BackgroundJobSpec
    thread: Thread | None = None
    state: BackgroundJobState = field(init=False)

    def __post_init__(self) -> None:
        self.state = BackgroundJobState(self.spec.name)


class BackgroundThreadSupervisor:
    """One owner for Brain background threads.

    The supervisor never silently creates duplicate jobs. A failed job is
    restarted with bounded exponential backoff. Shutdown is cooperative first.
    """

    def __init__(self, *, join_timeout_seconds: float = 5.0) -> None:
        if join_timeout_seconds <= 0:
            raise ValueError("BACKGROUND_JOIN_TIMEOUT_INVALID")
        self.join_timeout_seconds = join_timeout_seconds
        self._stop = Event()
        self._lock = Lock()
        self._jobs: dict[str, _RuntimeJob] = {}
        self._started = False

    def register(self, spec: BackgroundJobSpec) -> None:
        spec.validate()
        with self._lock:
            if self._started:
                raise RuntimeError("BACKGROUND_REGISTER_AFTER_START")
            if spec.name in self._jobs:
                raise RuntimeError("BACKGROUND_JOB_ALREADY_REGISTERED:" + spec.name)
            self._jobs[spec.name] = _RuntimeJob(spec)

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            for job in self._jobs.values():
                job.thread = Thread(
                    target=self._run_job,
                    args=(job,),
                    name=f"brain-bg:{job.spec.name}",
                    daemon=False,
                )
                job.thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            threads = [j.thread for j in self._jobs.values() if j.thread is not None]
        deadline = time.monotonic() + self.join_timeout_seconds
        for thread in threads:
            remaining = max(0.0, deadline - time.monotonic())
            thread.join(remaining)

    def is_alive(self, name: str) -> bool:
        with self._lock:
            job = self._jobs.get(name)
            return bool(job and job.thread and job.thread.is_alive())

    def snapshot(self) -> dict:
        with self._lock:
            jobs = {
                name: {
                    **vars(job.state),
                    "alive": bool(job.thread and job.thread.is_alive()),
                }
                for name, job in self._jobs.items()
            }
            return {
                "ok": True,
                "running": self._started and not self._stop.is_set(),
                "stop_requested": self._stop.is_set(),
                "jobs": jobs,
            }

    def _run_job(self, job: _RuntimeJob) -> None:
        spec = job.spec
        if spec.initial_delay_seconds and self._stop.wait(spec.initial_delay_seconds):
            job.state.state = "STOPPED"
            return

        backoff = spec.interval_seconds
        while not self._stop.is_set():
            job.state.state = "RUNNING"
            job.state.last_started_at = time.time()
            job.state.started_at = job.state.started_at or job.state.last_started_at
            try:
                spec.target(self._stop)
                job.state.run_count += 1
                job.state.consecutive_failures = 0
                job.state.last_error = None
                job.state.state = "IDLE"
                backoff = spec.interval_seconds
            except Exception as exc:
                job.state.consecutive_failures += 1
                job.state.restart_count += 1
                job.state.last_error = f"{type(exc).__name__}:{exc}"
                job.state.state = "BACKOFF"
                traceback.print_exc()
                if not spec.restart_on_failure:
                    break
                backoff = min(
                    spec.max_backoff_seconds,
                    max(spec.interval_seconds, backoff * 2),
                )
            finally:
                job.state.last_finished_at = time.time()

            if self._stop.wait(backoff):
                break

        job.state.state = "STOPPED"


class PeriodicBackgroundWorker:
    """Adapter for a bounded periodic callback."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self.callback = callback

    def __call__(self, stop: Event) -> None:
        if stop.is_set():
            return
        self.callback()

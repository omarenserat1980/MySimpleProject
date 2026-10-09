from __future__ import annotations

"""Brain-owned bounded background thread runtime.

Threads are workers, never independent authorities. One supervisor owns their
lifecycle and resource budget. Execution authority remains in Brain gateways.
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
    priority: int = 50
    weight: int = 1

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("BACKGROUND_JOB_NAME_REQUIRED")
        if self.interval_seconds <= 0:
            raise ValueError("BACKGROUND_JOB_INTERVAL_INVALID")
        if self.initial_delay_seconds < 0:
            raise ValueError("BACKGROUND_JOB_INITIAL_DELAY_INVALID")
        if self.max_backoff_seconds < self.interval_seconds:
            raise ValueError("BACKGROUND_JOB_MAX_BACKOFF_INVALID")
        if not 0 <= self.priority <= 100:
            raise ValueError("BACKGROUND_JOB_PRIORITY_INVALID")
        if self.weight < 1:
            raise ValueError("BACKGROUND_JOB_WEIGHT_INVALID")


@dataclass
class BackgroundJobState:
    name: str
    priority: int = 50
    weight: int = 1
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
        self.state = BackgroundJobState(
            self.spec.name, priority=self.spec.priority, weight=self.spec.weight
        )


class BackgroundThreadSupervisor:
    """Single owner for Brain resident workers with a hard concurrency budget."""

    def __init__(
        self,
        *,
        join_timeout_seconds: float = 5.0,
        max_threads: int = 4,
    ) -> None:
        if join_timeout_seconds <= 0:
            raise ValueError("BACKGROUND_JOIN_TIMEOUT_INVALID")
        if max_threads < 1:
            raise ValueError("BACKGROUND_MAX_THREADS_INVALID")
        self.join_timeout_seconds = join_timeout_seconds
        self.max_threads = max_threads
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
            if len(self._jobs) >= self.max_threads:
                raise RuntimeError("BACKGROUND_THREAD_BUDGET_EXCEEDED")
            self._jobs[spec.name] = _RuntimeJob(spec)

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            # Priority is scheduling intent only; it never changes authority.
            ordered = sorted(self._jobs.values(), key=lambda j: (-j.spec.priority, j.spec.name))
            for job in ordered:
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
            alive = sum(1 for job in self._jobs.values() if job.thread and job.thread.is_alive())
            return {
                "ok": True,
                "running": self._started and not self._stop.is_set(),
                "stop_requested": self._stop.is_set(),
                "max_threads": self.max_threads,
                "registered_threads": len(self._jobs),
                "alive_threads": alive,
                "budget_available": max(0, self.max_threads - len(self._jobs)),
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
                backoff = min(spec.max_backoff_seconds, max(spec.interval_seconds, backoff * 2))
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

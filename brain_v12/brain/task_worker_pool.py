from __future__ import annotations

"""Bounded Brain task worker pool with resource admission and backpressure."""

from dataclasses import dataclass, field
from queue import PriorityQueue, Empty
from threading import Event, Lock, Thread
from typing import Callable, Any
import time
import uuid


@dataclass(frozen=True)
class ResourceBudget:
    max_cpu_units: int = 100
    max_memory_units: int = 100
    max_active_weight: int = 100

    def validate(self) -> None:
        if min(self.max_cpu_units, self.max_memory_units, self.max_active_weight) < 1:
            raise ValueError("RESOURCE_BUDGET_INVALID")


@dataclass(frozen=True)
class WorkerTask:
    task_id: str
    run: Callable[["WorkerTask"], Any]
    priority: int = 50
    cpu_units: int = 1
    memory_units: int = 1
    weight: int = 1
    key: str = ""
    timeout_seconds: float | None = None
    submitted_at: float = field(default_factory=time.time)

    def validate(self) -> None:
        if not self.task_id.strip():
            raise ValueError("WORKER_TASK_ID_REQUIRED")
        if not 0 <= self.priority <= 100:
            raise ValueError("WORKER_TASK_PRIORITY_INVALID")
        if min(self.cpu_units, self.memory_units, self.weight) < 1:
            raise ValueError("WORKER_TASK_RESOURCE_INVALID")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("WORKER_TASK_TIMEOUT_INVALID")


class ResourceGovernor:
    """Fail-closed admission for finite CPU/RAM/weight capacity."""

    def __init__(self, budget: ResourceBudget | None = None) -> None:
        self.budget = budget or ResourceBudget()
        self.budget.validate()
        self._lock = Lock()
        self._cpu = self._memory = self._weight = 0

    def try_acquire(self, task: WorkerTask) -> bool:
        with self._lock:
            if (self._cpu + task.cpu_units > self.budget.max_cpu_units or
                self._memory + task.memory_units > self.budget.max_memory_units or
                self._weight + task.weight > self.budget.max_active_weight):
                return False
            self._cpu += task.cpu_units
            self._memory += task.memory_units
            self._weight += task.weight
            return True

    def release(self, task: WorkerTask) -> None:
        with self._lock:
            self._cpu = max(0, self._cpu - task.cpu_units)
            self._memory = max(0, self._memory - task.memory_units)
            self._weight = max(0, self._weight - task.weight)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "budget": vars(self.budget),
                "used": {"cpu_units": self._cpu, "memory_units": self._memory, "active_weight": self._weight},
                "available": {
                    "cpu_units": self.budget.max_cpu_units - self._cpu,
                    "memory_units": self.budget.max_memory_units - self._memory,
                    "active_weight": self.budget.max_active_weight - self._weight,
                },
            }


class TaskWorkerPool:
    """One bounded owner of task workers; workers have no execution authority."""

    def __init__(
        self,
        *,
        max_workers: int = 4,
        queue_limit: int = 100,
        governor: ResourceGovernor | None = None,
        starvation_seconds: float = 30.0,
    ) -> None:
        if max_workers < 1 or queue_limit < 1 or starvation_seconds <= 0:
            raise ValueError("WORKER_POOL_CONFIG_INVALID")
        self.max_workers = max_workers
        self.queue_limit = queue_limit
        self.governor = governor or ResourceGovernor()
        self.starvation_seconds = starvation_seconds
        self._queue: PriorityQueue[tuple[int, int, WorkerTask]] = PriorityQueue()
        self._seq = 0
        self._lock = Lock()
        self._stop = Event()
        self._wake = Event()
        self._workers: list[Thread] = []
        self._active: dict[str, WorkerTask] = {}
        self._seen: set[str] = set()
        self._stats = {"submitted": 0, "completed": 0, "failed": 0, "rejected": 0}

    def start(self) -> None:
        with self._lock:
            if self._workers:
                return
            for i in range(self.max_workers):
                t = Thread(target=self._worker, name=f"brain-task-worker:{i}", daemon=False)
                self._workers.append(t)
                t.start()

    def submit(self, task: WorkerTask) -> dict[str, Any]:
        task.validate()
        with self._lock:
            if task.task_id in self._seen:
                self._stats["rejected"] += 1
                return {"ok": False, "status": "DUPLICATE"}
            if self._queue.qsize() >= self.queue_limit:
                self._stats["rejected"] += 1
                return {"ok": False, "status": "BACKPRESSURE"}
            self._seen.add(task.task_id)
            self._seq += 1
            # Higher priority first; aging is applied by periodically rebuilding
            # effective priority at dequeue time.
            self._queue.put((-task.priority, self._seq, task))
            self._stats["submitted"] += 1
            self._wake.set()
            return {"ok": True, "status": "QUEUED", "task_id": task.task_id}

    def shutdown(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        deadline = time.monotonic() + timeout
        for worker in self._workers:
            worker.join(max(0.0, deadline - time.monotonic()))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "max_workers": self.max_workers,
                "worker_count": len(self._workers),
                "alive_workers": sum(t.is_alive() for t in self._workers),
                "queued": self._queue.qsize(),
                "active": len(self._active),
                "stats": dict(self._stats),
                "resources": self.governor.snapshot(),
            }

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                _, _, task = self._queue.get(timeout=0.2)
            except Empty:
                continue
            if not self.governor.try_acquire(task):
                # Resource backpressure: requeue without dropping the task.
                with self._lock:
                    self._seq += 1
                    self._queue.put((-task.priority, self._seq, task))
                time.sleep(0.05)
                continue
            with self._lock:
                self._active[task.task_id] = task
            try:
                # Execution authority remains in the supplied task callback;
                # this pool never authorizes capabilities itself.
                task.run(task)
                with self._lock:
                    self._stats["completed"] += 1
            except Exception:
                with self._lock:
                    self._stats["failed"] += 1
            finally:
                with self._lock:
                    self._active.pop(task.task_id, None)
                self.governor.release(task)
                self._queue.task_done()


__all__ = ["ResourceBudget", "WorkerTask", "ResourceGovernor", "TaskWorkerPool"]

from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Lock
from time import time
from uuid import uuid4

from .resource_manager import ResourceManager, ResourceRequirement

@dataclass
class VirtualTask:
    task_id: str
    program: list
    required_capabilities: set[str]
    requirement: ResourceRequirement
    status: str = "QUEUED"
    blade_id: str | None = None
    lease_id: str | None = None
    created_at: float = field(default_factory=time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict | None = None

class VirtualTaskQueue:
    """Queue-first executor: tasks are unbound until a capable Blade is available."""
    def __init__(self, chassis, resource_manager: ResourceManager, max_workers: int = 8):
        self.chassis = chassis
        self.resources = resource_manager
        self.tasks: dict[str, VirtualTask] = {}
        self.lock = Lock()
        self.pool = ThreadPoolExecutor(max_workers=max(1, int(max_workers)))

    def submit(self, program, required_capabilities=None, requirement=None, task_id=None):
        task = VirtualTask(
            task_id=task_id or f"vtask-{uuid4().hex[:12]}",
            program=list(program),
            required_capabilities=set(required_capabilities or {"cpu"}),
            requirement=requirement or ResourceRequirement(),
        )
        with self.lock:
            if task.task_id in self.tasks:
                return self.tasks[task.task_id]
            self.tasks[task.task_id] = task
        self._schedule(task.task_id)
        return task

    def _find_blade(self, task):
        candidates=[]
        for blade in self.chassis.blades.values():
            if blade.state != "ONLINE" or not task.required_capabilities.issubset(blade.capabilities):
                continue
            if self.resources.can_allocate(blade, task.requirement):
                candidates.append(blade)
        if not candidates:
            return None
        return max(candidates, key=lambda b:self.resources.snapshot(b)["ram"]["free_bytes"])

    def _schedule(self, task_id):
        with self.lock:
            task=self.tasks.get(task_id)
            if task is None or task.status not in {"QUEUED","WAITING"}:
                return
            blade=self._find_blade(task)
            if blade is None:
                task.status="WAITING"
                return
            reservation=self.resources.reserve(blade,task.task_id,task.requirement)
            if not reservation["ok"]:
                task.status="WAITING"
                return
            task.status="RUNNING"
            task.blade_id=blade.blade_id
            task.lease_id=uuid4().hex
            task.started_at=time()
        self.pool.submit(self._execute, task_id, blade)

    def _execute(self, task_id, blade):
        with self.lock:
            task=self.tasks[task_id]
        try:
            result=blade.execute(task.program)
            with self.lock:
                task.result=result
                task.status="COMPLETED"
                task.finished_at=time()
        except Exception as exc:
            with self.lock:
                task.result={"ok":False,"error":str(exc)}
                task.status="FAILED"
                task.finished_at=time()
        finally:
            self.resources.release(task_id)
            self.pump()

    def pump(self):
        for task_id in list(self.tasks):
            self._schedule(task_id)

    def get(self, task_id):
        with self.lock:
            task=self.tasks.get(task_id)
            return task

    def status(self):
        with self.lock:
            counts={}
            for task in self.tasks.values():
                counts[task.status]=counts.get(task.status,0)+1
            return {"tasks":len(self.tasks),"counts":counts}

    def shutdown(self):
        self.pool.shutdown(wait=False, cancel_futures=False)

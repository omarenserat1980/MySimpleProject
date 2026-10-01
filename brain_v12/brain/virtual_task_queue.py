from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Lock
from time import time
from uuid import uuid4
import json

from .resource_manager import ResourceManager, ResourceRequirement
from .durable_task_store import DurableTaskStore

@dataclass
class VirtualTask:
    task_id: str
    program: list
    required_capabilities: set[str]
    requirement: ResourceRequirement
    status: str = "QUEUED"
    blade_id: str | None = None
    lease_id: str | None = None
    lease_expires_at: float | None = None
    created_at: float = field(default_factory=time)
    started_at: float | None = None
    finished_at: float | None = None
    result: dict | None = None

class VirtualTaskQueue:
    """Durable queue-first executor; task state survives process restart."""
    def __init__(self, chassis, resource_manager: ResourceManager, max_workers=8,
                 store_path="brain6_artifacts/virtual_tasks/tasks.db"):
        self.chassis=chassis
        self.resources=resource_manager
        self.tasks={}
        self.lock=Lock()
        self.pool=ThreadPoolExecutor(max_workers=max(1,int(max_workers)))
        self.store=DurableTaskStore(store_path)

    def submit(self, program, required_capabilities=None, requirement=None, task_id=None):
        task=VirtualTask(task_id or f"vtask-{uuid4().hex[:12]}",list(program),
                         set(required_capabilities or {"cpu"}),requirement or ResourceRequirement())
        with self.lock:
            existing=self.tasks.get(task.task_id)
            if existing: return existing
            self.store.submit(task.task_id,{"program":task.program,
                "required_capabilities":sorted(task.required_capabilities),
                "requirement":task.requirement.__dict__})
            self.tasks[task.task_id]=task
        self._schedule(task.task_id)
        return task

    def _find_blade(self,task):
        candidates=[b for b in self.chassis.blades.values()
            if b.state=="ONLINE" and task.required_capabilities.issubset(b.capabilities)
            and self.resources.can_allocate(b,task.requirement)]
        return max(candidates,key=lambda b:self.resources.snapshot(b)["ram"]["free_bytes"]) if candidates else None

    def _schedule(self,task_id):
        with self.lock:
            task=self.tasks.get(task_id)
            if not task or task.status not in {"QUEUED","WAITING"}: return
            blade=self._find_blade(task)
            if blade is None:
                task.status="WAITING"; return
            reservation=self.resources.reserve(blade,task.task_id,task.requirement)
            if not reservation["ok"]:
                task.status="WAITING"; return
            claimed=self.store.claim(task.task_id,blade.blade_id,300)
            if claimed is None:
                self.resources.release(task.task_id)
                task.status="WAITING"; return
            task.status="RUNNING"; task.blade_id=blade.blade_id
            task.lease_id=claimed["lease_id"]; task.lease_expires_at=claimed["lease_expires_at"]
            task.started_at=time()
        self.pool.submit(self._execute,task_id,blade)

    def _execute(self,task_id,blade):
        task=self.tasks[task_id]
        try:
            result=blade.execute(task.program)
            with self.lock:
                task.result=result; task.status="COMPLETED"; task.lease_expires_at=None; task.finished_at=time()
                self.store.finish(task_id,True,result)
        except Exception as exc:
            with self.lock:
                task.result={"ok":False,"error":str(exc)}; task.status="FAILED"; task.lease_expires_at=None; task.finished_at=time()
                self.store.finish(task_id,False,task.result)
        finally:
            self.resources.release(task_id)
            self.pump()

    def heartbeat(self,task_id,lease_id):
        with self.lock:
            task=self.tasks.get(task_id)
            if not task or task.status!="RUNNING" or task.lease_id!=lease_id:
                return {"ok":False,"status":"LEASE_INVALID"}
            if not self.store.heartbeat(task_id,lease_id,300): return {"ok":False,"status":"LEASE_INVALID"}
            task.lease_expires_at=time()+300
            return {"ok":True,"status":"HEARTBEAT","task_id":task_id}

    def recover_expired(self):
        count=self.store.recover_expired()
        recovered=[]
        with self.lock:
            for task in self.tasks.values():
                if task.status=="RUNNING" and task.lease_expires_at and task.lease_expires_at<time():
                    self.resources.release(task.task_id)
                    task.status="QUEUED"; task.blade_id=None; task.lease_id=None; task.lease_expires_at=None
                    recovered.append(task.task_id)
        return recovered if recovered else count

    def pump(self):
        self.recover_expired()
        for task_id in list(self.tasks): self._schedule(task_id)

    def get(self,task_id):
        with self.lock:
            task=self.tasks.get(task_id)
            if task: return task
        row=self.store.get(task_id)
        if not row: return None
        p=json.loads(row["payload"])
        req=ResourceRequirement(**p.get("requirement",{}))
        return VirtualTask(task_id,p.get("program",[]),set(p.get("required_capabilities",[])),req,
                           row["status"],row["blade_id"],row["lease_id"],row["lease_expires_at"],
                           row["created_at"],None,None,p if row["status"] in {"COMPLETED","FAILED"} else None)

    def status(self):
        return {"tasks":sum(self.store.counts().values()),"counts":self.store.counts()}

    def shutdown(self):
        self.pool.shutdown(wait=False,cancel_futures=False)
        self.store.close()

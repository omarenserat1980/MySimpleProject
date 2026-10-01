from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass,field
from threading import RLock
from time import time
from uuid import uuid4
import json
from .resource_manager import ResourceManager,ResourceRequirement
from .durable_task_store import DurableTaskStore

@dataclass
class VirtualTask:
    task_id:str
    program:list
    required_capabilities:set[str]
    requirement:ResourceRequirement
    status:str="QUEUED"
    blade_id:str|None=None
    lease_id:str|None=None
    lease_expires_at:float|None=None
    created_at:float=field(default_factory=time)
    started_at:float|None=None
    finished_at:float|None=None
    result:dict|None=None
    attempt:int=0
    idempotency_key:str|None=None

class VirtualTaskQueue:
    """Durable queue with startup recovery and explicit verification boundary."""
    def __init__(self,chassis,resource_manager,max_workers=8,store_path="brain6_artifacts/virtual_tasks/tasks.db"):
        self.chassis=chassis; self.resources=resource_manager; self.tasks={}; self.lock=RLock()
        self.pool=ThreadPoolExecutor(max_workers=max(1,int(max_workers))); self.store=DurableTaskStore(store_path)
        self._recover_on_start()

    def _row_to_task(self,row):
        spec=json.loads(row["payload"]); result=json.loads(row["result_json"]) if row.get("result_json") else None
        req=ResourceRequirement(**spec.get("requirement",{}))
        return VirtualTask(row["task_id"],spec.get("program",[]),set(spec.get("required_capabilities",[])),req,
          row["status"],row["blade_id"],row["lease_id"],row["lease_expires_at"],row["created_at"],None,None,result,
          int(row.get("attempt") or 0),row.get("idempotency_key"))

    def _recover_on_start(self):
        # A new process cannot trust old in-memory resource reservations. Requeue stale RUNNING work first.
        self.store.recover_expired()
        for row in self.store.list_active():
            task=self._row_to_task(row)
            if task.status=="RUNNING":
                # Conservative restart rule: old executor ownership is not provable here.
                self.store.requeue(task.task_id)
                task.status="QUEUED"; task.blade_id=None; task.lease_id=None; task.lease_expires_at=None
            self.tasks[task.task_id]=task
        self.pump()

    def submit(self,program,required_capabilities=None,requirement=None,task_id=None,idempotency_key=None):
        task_id=task_id or f"vtask-{uuid4().hex[:12]}"
        existing=self.store.submit(task_id,{"program":list(program),"required_capabilities":sorted(required_capabilities or {"cpu"}),
          "requirement":(requirement or ResourceRequirement()).__dict__},idempotency_key)
        task=self._row_to_task(existing)
        with self.lock: self.tasks[task.task_id]=task
        self._schedule(task.task_id)
        return task

    def _find_blade(self,task):
        candidates=[b for b in self.chassis.blades.values() if b.state=="ONLINE"
          and task.required_capabilities.issubset(b.capabilities) and self.resources.can_allocate(b,task.requirement)]
        return max(candidates,key=lambda b:self.resources.snapshot(b)["ram"]["free_bytes"]) if candidates else None

    def _schedule(self,task_id):
        with self.lock:
            task=self.tasks.get(task_id)
            if not task or task.status not in {"QUEUED","WAITING"}: return
            blade=self._find_blade(task)
            if blade is None: task.status="WAITING"; return
            reservation=self.resources.reserve(blade,task.task_id,task.requirement)
            if not reservation["ok"]: task.status="WAITING"; return
            claimed=self.store.claim(task.task_id,blade.blade_id,300)
            if claimed is None:
                self.resources.release(task.task_id); task.status="WAITING"; return
            task.status="RUNNING"; task.blade_id=blade.blade_id; task.lease_id=claimed["lease_id"]
            task.lease_expires_at=claimed["lease_expires_at"]; task.attempt=claimed["attempt"]; task.started_at=time()
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
            self.resources.release(task_id); self.pump()

    def heartbeat(self,task_id,lease_id):
        with self.lock:
            task=self.tasks.get(task_id)
            if not task or task.status!="RUNNING" or task.lease_id!=lease_id: return {"ok":False,"status":"LEASE_INVALID"}
            if not self.store.heartbeat(task_id,lease_id,300): return {"ok":False,"status":"LEASE_INVALID"}
            task.lease_expires_at=time()+300
            return {"ok":True,"status":"HEARTBEAT","task_id":task_id}

    def recover_expired(self):
        ids=self.store.recover_expired()
        with self.lock:
            for task_id in ids:
                task=self.tasks.get(task_id)
                if task:
                    self.resources.release(task_id); task.status="QUEUED"; task.blade_id=None; task.lease_id=None; task.lease_expires_at=None
        self.pump()
        return ids

    def pump(self):
        for task_id in list(self.tasks): self._schedule(task_id)

    def get(self,task_id):
        with self.lock:
            if task_id in self.tasks: return self.tasks[task_id]
        row=self.store.get(task_id)
        return self._row_to_task(row) if row else None

    def status(self):
        counts=self.store.counts(); return {"tasks":sum(counts.values()),"counts":counts}

    def shutdown(self):
        self.pool.shutdown(wait=False,cancel_futures=False); self.store.close()

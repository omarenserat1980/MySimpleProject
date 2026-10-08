"""Durable worker registry facade for Brain routing.

The registry derives worker availability from the existing DeviceBridge agent
heartbeats and optional cloud/local registrations. It never claims a worker is
online without a fresh heartbeat/registration.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import time
from .workload_router import WorkerTarget

@dataclass
class WorkerRecord:
    worker_id:str
    kind:str
    capabilities:frozenset[str]
    online:bool
    last_seen:float
    lease_until:float=0.0

class WorkerRegistry:
    def __init__(self, device_bridge=None, ttl_seconds:int=15):
        self.device_bridge=device_bridge
        self.ttl_seconds=max(5,int(ttl_seconds))
        self._workers={}

    def register(self, worker_id, kind, capabilities=(), lease_seconds=30, now=None):
        now=time.time() if now is None else float(now)
        rec=WorkerRecord(worker_id,str(kind),frozenset(capabilities),True,now,now+max(5,int(lease_seconds)))
        self._workers[worker_id]=rec
        return self.snapshot(now)

    def heartbeat(self, worker_id, capabilities=None, lease_seconds=30, now=None):
        now=time.time() if now is None else float(now)
        old=self._workers.get(worker_id)
        caps=frozenset(capabilities) if capabilities is not None else (old.capabilities if old else frozenset())
        kind=old.kind if old else "local"
        return self.register(worker_id,kind,caps,lease_seconds,now)

    def _device_workers(self, now):
        if not self.device_bridge:
            return []
        out=[]
        for item in self.device_bridge.agent_status().get("agents",[]):
            if item.get("online"):
                out.append(WorkerTarget(item["agent_id"],"device",frozenset({"device","termux"}),True))
        return out

    def targets(self, now=None):
        now=time.time() if now is None else float(now)
        out=[]
        for rec in self._workers.values():
            online=rec.online and rec.lease_until >= now
            out.append(WorkerTarget(rec.worker_id,rec.kind,rec.capabilities,online))
        out.extend(self._device_workers(now))
        return out

    def snapshot(self, now=None):
        now=time.time() if now is None else float(now)
        return {"ok":True,"workers":[{"worker_id":w.worker_id,"kind":w.kind,"capabilities":sorted(w.capabilities),"online":w.online,"last_seen":w.last_seen,"lease_until":w.lease_until} for w in self._workers.values()],
                "device_workers":[asdict(x) for x in self._device_records(now)],"targets":[{"worker_id":x.worker_id,"kind":x.kind,"capabilities":sorted(x.capabilities),"online":x.online} for x in self.targets(now)]}

    def _device_records(self, now):
        return [WorkerRecord(x.worker_id,x.kind,x.capabilities,x.online,now,now+self.ttl_seconds) for x in self._device_workers(now)]

    def unregister(self, worker_id):
        self._workers.pop(worker_id,None)
        return self.snapshot()

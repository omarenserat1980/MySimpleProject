"""Cloud MAX resource fabric: bounded leases over existing Brain resources."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import time
from .cloud_hardware import HardwareManifest, WorkloadRequirement, satisfies, select_executor

@dataclass
class ExecutorLease:
    executor_id: str
    task_id: str
    issued_at: float
    expires_at: float
    heartbeat_at: float
    state: str = "ACTIVE"

@dataclass
class CloudResourceFabric:
    manifests: dict[str, HardwareManifest] = field(default_factory=dict)
    leases: dict[str, ExecutorLease] = field(default_factory=dict)
    reservations: dict[str, str] = field(default_factory=dict)

    def register(self, manifest):
        manifest.validate()
        self.manifests[manifest.machine_id] = manifest
        return {"ok": True, "status": "REGISTERED", "executor_id": manifest.machine_id}

    def heartbeat(self, executor_id, now=None):
        now = time() if now is None else now
        manifest = self.manifests.get(executor_id)
        if manifest is None: return {"ok": False, "status": "EXECUTOR_NOT_FOUND"}
        if manifest.state == "quarantined": return {"ok": False, "status": "EXECUTOR_QUARANTINED"}
        for lease in self.leases.values():
            if lease.executor_id == executor_id and lease.state == "ACTIVE": lease.heartbeat_at = now
        return {"ok": True, "status": "HEARTBEAT_ACCEPTED", "executor_id": executor_id}

    def reap_expired(self, now=None):
        now = time() if now is None else now
        expired=[]
        for task_id, lease in list(self.leases.items()):
            if lease.state == "ACTIVE" and lease.expires_at <= now:
                lease.state="EXPIRED"; expired.append(task_id)
        return expired

    def acquire(self, task_id, req, lease_seconds=300, now=None):
        now = time() if now is None else now
        self.reap_expired(now)
        existing=self.leases.get(task_id)
        if existing and existing.state=="ACTIVE":
            return {"ok":True,"status":"ALREADY_LEASED","executor_id":existing.executor_id,"task_id":task_id}
        busy={x.executor_id for x in self.leases.values() if x.state=="ACTIVE"}
        candidates=[m for m in self.manifests.values() if m.machine_id not in busy and satisfies(m,req)]
        selected=select_executor(candidates,req)
        if selected is None: return {"ok":False,"status":"NO_CAPABLE_EXECUTOR","task_id":task_id}
        lease=ExecutorLease(selected.machine_id,task_id,now,now+lease_seconds,now)
        self.leases[task_id]=lease; self.reservations[task_id]=selected.machine_id
        return {"ok":True,"status":"LEASE_ACQUIRED","task_id":task_id,"executor_id":selected.machine_id,"expires_at":lease.expires_at}

    def release(self, task_id):
        lease=self.leases.pop(task_id,None); self.reservations.pop(task_id,None)
        return {"ok":lease is not None,"status":"RELEASED" if lease else "NOT_FOUND","task_id":task_id}

    def quarantine(self, executor_id, reason="health_failure"):
        manifest=self.manifests.get(executor_id)
        if manifest is None: return {"ok":False,"status":"EXECUTOR_NOT_FOUND"}
        manifest.state="quarantined"
        for lease in self.leases.values():
            if lease.executor_id==executor_id and lease.state=="ACTIVE": lease.state="REVOKED"
        return {"ok":True,"status":"QUARANTINED","executor_id":executor_id,"reason":reason}

    def status(self):
        return {"ok":True,"executors":len(self.manifests),
                "online":sum(m.state=="online" for m in self.manifests.values()),
                "leases_active":sum(x.state=="ACTIVE" for x in self.leases.values()),
                "leases":[x.__dict__.copy() for x in self.leases.values()]}

"""Durable provider-neutral Brain job dispatcher.

This module is intentionally dependency-free. It provides the contract between the
Brain control plane and execution workers. It does not execute arbitrary commands.
"""

from __future__ import annotations
import hashlib, json, time, uuid
from pathlib import Path

TERMINAL = {"VERIFIED", "RELEASED", "CANCELLED", "BLOCKED"}
ALLOWED = {"DISCOVERED","PLANNED","READY","LEASED","RUNNING","VERIFIED","RELEASED","FAILED","RETRYING","CANCELLED","BLOCKED"}

class JobDispatcher:
    def __init__(self, root="brain6_artifacts/dispatcher", max_attempts=3, lease_seconds=60):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.jobs=self.root/"jobs.jsonl"; self.events=self.root/"events.jsonl"
        self.max_attempts=max(1,min(int(max_attempts),5))
        self.lease_seconds=max(10,int(lease_seconds))

    def _write(self,path,row):
        with path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")

    def _event(self,job_id,event,data=None):
        self._write(self.events,{"ts":time.time(),"job_id":job_id,"event":event,"data":data or {}})

    def create(self, task, capabilities, payload=None):
        if not task or not capabilities:
            raise ValueError("task_and_capabilities_required")
        job={"job_id":uuid.uuid4().hex,"task":task,
             "required_capabilities":sorted(set(capabilities)),
             "payload":payload or {},"status":"DISCOVERED","attempt":0,
             "max_attempts":self.max_attempts,"worker_id":None,
             "lease_id":None,"lease_expires_at":None,"created_at":time.time(),
             "updated_at":time.time(),"evidence":None}
        self._write(self.jobs,job); self._event(job["job_id"],"created",{"task":task})
        return job

    @staticmethod
    def worker_can_run(worker, required):
        caps=set(worker.get("capabilities",[]))
        return worker.get("status")=="healthy" and set(required).issubset(caps)

    def plan(self,job):
        if job["status"]!="DISCOVERED": raise ValueError("invalid_transition")
        job=dict(job); job["status"]="PLANNED"; job["updated_at"]=time.time()
        self._write(self.jobs,job); self._event(job["job_id"],"planned")
        return job

    def select_worker(self,job,workers):
        candidates=[w for w in workers if self.worker_can_run(w,job["required_capabilities"])]
        if not candidates: return None
        return sorted(candidates,key=lambda w:w["worker_id"])[0]

    def acquire(self,job,worker):
        if job["status"] not in {"PLANNED","RETRYING","READY"}:
            raise ValueError("job_not_assignable")
        if not self.worker_can_run(worker,job["required_capabilities"]):
            raise ValueError("worker_capability_mismatch")
        now=time.time()
        attempt=job["attempt"]+1
        if attempt>job["max_attempts"]: raise ValueError("attempt_limit")
        lease_id=uuid.uuid4().hex
        out=dict(job,status="LEASED",attempt=attempt,worker_id=worker["worker_id"],
                 lease_id=lease_id,lease_expires_at=now+self.lease_seconds,updated_at=now)
        self._write(self.jobs,out); self._event(out["job_id"],"leased",{"worker_id":worker["worker_id"],"attempt":attempt})
        return out

    def start(self,job):
        if job["status"]!="LEASED": raise ValueError("lease_required")
        if not job["lease_id"] or (job["lease_expires_at"] or 0)<=time.time():
            return self.fail(job,"lease_expired")
        out=dict(job,status="RUNNING",updated_at=time.time())
        self._write(self.jobs,out); self._event(out["job_id"],"running",{"attempt":out["attempt"]})
        return out

    def renew(self,job):
        if job["status"]!="RUNNING": return False
        if (job["lease_expires_at"] or 0)<=time.time(): return False
        out=dict(job,lease_expires_at=time.time()+self.lease_seconds,updated_at=time.time())
        self._write(self.jobs,out); self._event(out["job_id"],"lease_renewed")
        return out

    def verify(self,job,evidence):
        if job["status"]!="RUNNING": raise ValueError("job_not_running")
        if not isinstance(evidence,dict) or not evidence.get("verified"):
            return self.fail(job,"verification_failed",evidence)
        digest=hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()
        out=dict(job,status="VERIFIED",evidence={**evidence,"evidence_digest":digest},
                 lease_expires_at=None,updated_at=time.time())
        self._write(self.jobs,out); self._event(out["job_id"],"verified",{"digest":digest})
        return out

    def fail(self,job,reason,evidence=None):
        now=time.time()
        status="RETRYING" if job["attempt"]<job["max_attempts"] else "FAILED"
        out=dict(job,status=status,updated_at=now,lease_expires_at=None,
                 evidence={"verified":False,"reason":reason,"details":evidence or {}})
        self._write(self.jobs,out); self._event(out["job_id"],"failed",{"reason":reason,"next":status})
        return out

    def release(self,job):
        if job["status"]!="VERIFIED": raise ValueError("verification_required")
        out=dict(job,status="RELEASED",updated_at=time.time(),lease_id=None)
        self._write(self.jobs,out); self._event(out["job_id"],"released")
        return out

    def snapshot(self):
        latest={}
        if not self.jobs.exists(): return []
        for line in self.jobs.read_text(encoding="utf-8").splitlines():
            if line:
                row=json.loads(line); latest[row["job_id"]]=row
        return sorted(latest.values(),key=lambda x:x["created_at"])

if __name__=="__main__":
    d=JobDispatcher()
    j=d.plan(d.create("probe",["python"],{"safe":True}))
    w={"worker_id":"self-test","capabilities":["python"],"status":"healthy"}
    j=d.start(d.acquire(j,w))
    j=d.verify(j,{"verified":True,"result":"self_test"})
    j=d.release(j)
    print(json.dumps({"status":j["status"],"job_id":j["job_id"]},indent=2))

"""Durable Brain control plane with append-only events, bounded attempts and recovery metadata."""
from __future__ import annotations
import hashlib, json, os, time, uuid
from pathlib import Path

TERMINAL={"completed","failed","blocked","cancelled"}
class ControlPlane:
    def __init__(self, root="brain6_artifacts/control_plane"):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.jobs=self.root/"jobs.jsonl"; self.events=self.root/"events.jsonl"
    def _append(self,path,row):
        with path.open("a",encoding="utf-8") as f: f.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    def _last_event_digest(self):
        if not self.events.exists(): return "GENESIS"
        lines=self.events.read_text(encoding="utf-8").splitlines()
        if not lines:return "GENESIS"
        return json.loads(lines[-1]).get("digest","GENESIS")
    def create(self,task,steps,max_attempts=3,budget=10,idempotency_key=None):
        key=idempotency_key or uuid.uuid4().hex
        if self.jobs.exists():
            for line in self.jobs.read_text(encoding="utf-8").splitlines():
                if line and json.loads(line).get("idempotency_key")==key:return json.loads(line)
        now=time.time(); job={"job_id":uuid.uuid4().hex,"task":task,"steps":list(steps),"step_index":0,"status":"ready","attempts":0,"max_attempts":max(1,min(int(max_attempts),5)),"budget":max(0,float(budget)),"created_at":now,"updated_at":now,"checkpoint":None,"idempotency_key":key,"lease_id":None,"lease_expires_at":None}
        self._append(self.jobs,job); self.audit(job["job_id"],"created",{"task":task}); return job
    def checkpoint(self,job,step_index,output=None):
        job=dict(job); job["step_index"]=step_index; job["checkpoint"]={"step_index":step_index,"output":output}; job["status"]="ready" if step_index<len(job["steps"]) else "completed"; job["updated_at"]=time.time(); self._append(self.jobs,job); self.audit(job["job_id"],"checkpoint",{"step_index":step_index}); return job
    def can_run(self,job,external=False):
        if job["status"] in TERMINAL:return False,"terminal"
        if job["attempts"]>=job["max_attempts"]:return False,"attempt_limit"
        if job["budget"]<=0:return False,"budget_exhausted"
        if external:return False,"external_action_requires_policy_gate"
        return True,"allowed"
    def start_attempt(self,job,lease_seconds=300):
        ok,reason=self.can_run(job)
        if not ok:
            job=dict(job); job["status"]="blocked" if reason.startswith("external") else "failed"; self._append(self.jobs,job); self.audit(job["job_id"],"blocked",{"reason":reason}); return job
        now=time.time(); job=dict(job); job["status"]="running"; job["attempts"]+=1; job["budget"]-=1; job["updated_at"]=now; job["lease_id"]=uuid.uuid4().hex; job["lease_expires_at"]=now+max(5,int(lease_seconds)); self._append(self.jobs,job); self.audit(job["job_id"],"attempt_started",{"attempt":job["attempts"],"lease_id":job["lease_id"]}); return job
    def heartbeat(self,job,lease_id):
        if job.get("lease_id")!=lease_id or job.get("status")!="running": return {"ok":False,"reason":"LEASE_INVALID"}
        job=dict(job); job["lease_expires_at"]=time.time()+300; job["updated_at"]=time.time(); self._append(self.jobs,job); self.audit(job["job_id"],"heartbeat",{}); return {"ok":True,"job":job}
    def recover_expired(self,job):
        if job.get("status")=="running" and float(job.get("lease_expires_at") or 0)<time.time():
            job=dict(job); job["status"]="ready"; job["lease_id"]=None; job["lease_expires_at"]=None; job["updated_at"]=time.time(); self._append(self.jobs,job); self.audit(job["job_id"],"lease_recovered",{}); return job
        return job
    def audit(self,job_id,event,data=None):
        payload={"ts":time.time(),"job_id":job_id,"event":event,"data":data or {},"prev":self._last_event_digest()}; raw=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(",",":")); payload["digest"]=hashlib.sha256(raw.encode()).hexdigest(); self._append(self.events,payload); return payload["digest"]

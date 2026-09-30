"""Dependency-free Brain control plane.

Provides durable job state, bounded retries, policy gates, audit events and
checkpoint/resume semantics. It is intentionally backend-agnostic.
"""
from __future__ import annotations
import json, time, uuid
from pathlib import Path

TERMINAL={"completed","failed","blocked","cancelled"}

class ControlPlane:
    def __init__(self, root="brain6_artifacts/control_plane"):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.jobs=self.root/"jobs.jsonl"; self.events=self.root/"events.jsonl"

    def _append(self,path,row):
        with path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,ensure_ascii=False)+"\n")

    def create(self, task, steps, max_attempts=3, budget=10):
        job={"job_id":uuid.uuid4().hex,"task":task,"steps":steps,
             "step_index":0,"status":"ready","attempts":0,
             "max_attempts":max(1,min(int(max_attempts),5)),
             "budget":max(0,float(budget)),"created_at":time.time(),
             "updated_at":time.time(),"checkpoint":None}
        self._append(self.jobs,job); self.audit(job["job_id"],"created",{"task":task})
        return job

    def checkpoint(self,job,step_index,output=None):
        job=dict(job); job["step_index"]=step_index
        job["checkpoint"]={"step_index":step_index,"output":output}
        job["status"]="ready" if step_index < len(job["steps"]) else "completed"
        job["updated_at"]=time.time()
        self._append(self.jobs,job)
        self.audit(job["job_id"],"checkpoint",{"step_index":step_index})
        return job

    def can_run(self,job,external=False):
        if job["status"] in TERMINAL: return False,"terminal"
        if job["attempts"] >= job["max_attempts"]: return False,"attempt_limit"
        if job["budget"] <= 0: return False,"budget_exhausted"
        if external: return False,"external_action_requires_policy_gate"
        return True,"allowed"

    def start_attempt(self,job):
        ok,reason=self.can_run(job)
        if not ok:
            job=dict(job); job["status"]="blocked" if reason.startswith("external") else "failed"
            self._append(self.jobs,job); self.audit(job["job_id"],"blocked",{"reason":reason})
            return job
        job=dict(job); job["status"]="running"; job["attempts"]+=1; job["budget"]-=1
        job["updated_at"]=time.time(); self._append(self.jobs,job)
        self.audit(job["job_id"],"attempt_started",{"attempt":job["attempts"]})
        return job

    def audit(self,job_id,event,data=None):
        self._append(self.events,{"ts":time.time(),"job_id":job_id,"event":event,"data":data or {}})

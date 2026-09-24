"""Authenticated, allowlisted, persistent bridge between Brain V12 and a Termux device agent."""
from __future__ import annotations
import hmac, os, time
from uuid import uuid4

class DeviceBridge:
    ALLOWED_TASKS={"status":{}, "python_version":{}, "termux_path":{}, "platform":{}}

    def __init__(self, store):
        self.store=store
        self._last_seen=None

    def configured(self): return bool(os.getenv("V12_AGENT_KEY",""))

    def authenticate(self, supplied):
        expected=os.getenv("V12_AGENT_KEY","")
        return bool(expected and supplied and hmac.compare_digest(supplied,expected))

    def enqueue(self, task, params=None):
        if task not in self.ALLOWED_TASKS:
            return {"ok":False,"status":"TASK_NOT_ALLOWED","allowed":sorted(self.ALLOWED_TASKS)}
        item={"task_id":"DEV-"+uuid4().hex[:12],"task":task,"params":params or {},"created_at":time.time(),"status":"QUEUED"}
        self.store.device_task_create(item["task_id"],task,item["params"],item["created_at"])
        return {"ok":True,"task":item}

    def poll(self, agent_id):
        if not agent_id: return {"ok":False,"status":"AGENT_ID_REQUIRED"}
        self._last_seen=time.time()
        item=self.store.device_task_claim(agent_id)
        return {"ok":True,"task":item,"status":"IDLE" if item is None else "CLAIMED"}

    def report(self, task_id, agent_id, ok, result=None, error=""):
        status=self.store.device_task_report(task_id,agent_id,ok,result or {},error)
        if status is None: return {"ok":False,"status":"TASK_NOT_FOUND"}
        if status=="AGENT_MISMATCH": return {"ok":False,"status":status}
        return {"ok":True,"status":status,"task":self.store.device_task_get(task_id)}

    def result(self, task_id):
        item=self.store.device_task_get(task_id)
        return {"ok":bool(item),"task":item} if item else {"ok":False,"status":"RESULT_NOT_FOUND"}

    def wait_result(self, task_id, timeout=20):
        deadline=time.time()+max(.1,timeout)
        while time.time()<deadline:
            r=self.result(task_id)
            if r.get("ok") and r.get("task",{}).get("status") in ("COMPLETED","FAILED"): return r
            time.sleep(.5)
        return {"ok":False,"status":"RESULT_TIMEOUT","task_id":task_id}

    def status(self):
        counts=self.store.device_task_counts()
        return {"ok":True,"configured":self.configured(),"queued":counts.get("QUEUED",0),
                "pending":counts.get("CLAIMED",0),"completed":counts.get("COMPLETED",0),
                "failed":counts.get("FAILED",0),"last_agent_seen":self._last_seen}

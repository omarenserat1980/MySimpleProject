"""Brain Cloud ↔ Brain Termux execution bridge."""
from __future__ import annotations
import hashlib,hmac,os,time
from uuid import uuid4
from .device_sync_adapter import DeviceTaskSyncAdapter
AGENT_KEY_ENV="BRAIN_AGENT_KEY"; AGENT_KEY_SHA256_ENV="BRAIN_AGENT_KEY_SHA256"; ENABLE_ENV="BRAIN_ENABLE_DEVICE_BRIDGE"; HEARTBEAT_STALE="STALE"

class DeviceBridge:
    ALLOWED_TASKS={"status":{},"python_version":{},"platform":{},"brain_self_test":{},"cinematic_room13_render":{},
                   "brain_local_painter_draw":{},"brain_machine_cinema_60m":{},"brain_machine_cinema_120m":{}}
    def __init__(self,store,sync_adapter=None):
        self.store=store; self._last_seen=None
        self.sync_adapter=sync_adapter or DeviceTaskSyncAdapter(
            os.getenv("BRAIN_SYNC_QUEUE","brain6_artifacts/sync/device-sync.jsonl")
        )
    def configured(self): return bool(os.getenv(AGENT_KEY_ENV) or os.getenv(AGENT_KEY_SHA256_ENV) or os.getenv("BRAIN_EMULATOR_KEY"))
    def enabled(self): return os.getenv(ENABLE_ENV, "0").strip().lower() in {"1", "true", "yes", "on"} and self.configured()
    def auth_mode(self):
        if os.getenv(AGENT_KEY_ENV,""): return "DIRECT_KEY"
        if os.getenv(AGENT_KEY_SHA256_ENV,""): return "SHA256_KEY"
        if os.getenv("BRAIN_EMULATOR_KEY",""): return "BRAIN_EMULATOR_KEY"
        return "NOT_CONFIGURED"
    def authenticate(self,supplied):
        if not self.enabled() or not supplied:return False
        expected=os.getenv(AGENT_KEY_ENV,"") or os.getenv("BRAIN_EMULATOR_KEY","")
        if not expected:
            key_file=os.path.expanduser(os.getenv("BRAIN_AGENT_KEY_FILE") or os.getenv("V12_AGENT_KEY_FILE") or "~/v12-agent/agent.key")
            if key_file and os.path.isfile(key_file):
                try:
                    with open(key_file,encoding="utf-8") as f: expected=f.read().strip()
                except OSError: expected=""
        if expected and hmac.compare_digest(supplied,expected):return True
        expected_hash=os.getenv(AGENT_KEY_SHA256_ENV,"").strip().lower()
        return bool(expected_hash) and hmac.compare_digest(hashlib.sha256(supplied.encode()).hexdigest(),expected_hash)
    def enqueue(self,task,params=None):
        if not self.enabled(): return {"ok":False,"status":"BRIDGE_DISABLED"}
        if task not in self.ALLOWED_TASKS:return {"ok":False,"status":"TASK_NOT_ALLOWED","task":task}
        task_id="brain-termux-"+uuid4().hex
        self.store.device_task_create(task_id,task,params or {},time.time())
        self.sync_adapter.task_transition(task_id,status="QUEUED",task=task)
        return {"ok":True,"status":"QUEUED","task":self.store.device_task_get(task_id)}
    def poll(self,agent_id):
        if not self.enabled(): return {"ok":False,"status":"BRIDGE_DISABLED","task":None}
        task=self.store.device_task_claim(agent_id)
        if self.sync_adapter and task:
            self.sync_adapter.task_transition(task["task_id"],status="CLAIMED",agent_id=agent_id,task=task.get("task"))
        return {"ok":True,"status":"TASK_AVAILABLE" if task else "IDLE","task":task}
    def heartbeat(self,agent_id,metadata=None):
        if not self.enabled(): return {"ok":False,"status":"BRIDGE_DISABLED","agent_id":agent_id}
        self.store.device_agent_touch(agent_id); self._last_seen=time.time()
        self.sync_adapter.heartbeat(agent_id,metadata=metadata)
        return {"ok":True,"status":"HEARTBEAT","agent_id":agent_id,"metadata":metadata or {}}
    def report(self,task_id,agent_id,ok,result=None,error=""):
        if not self.enabled(): return {"ok":False,"status":"BRIDGE_DISABLED"}
        status=self.store.device_task_report(task_id,agent_id,ok,result or {},error)
        if status is None:return {"ok":False,"status":"TASK_NOT_FOUND"}
        if status=="AGENT_MISMATCH":return {"ok":False,"status":status}
        item=self.store.device_task_get(task_id) or {}
        self.sync_adapter.task_transition(task_id,status=status,agent_id=agent_id,task=item.get("task"),
                                          result=result or {},error=error,evidence_ref=(result or {}).get("evidence_ref"))
        return {"ok":True,"status":status,"task":item}
    def result(self,task_id):
        item=self.store.device_task_get(task_id); return {"ok":bool(item),"task":item} if item else {"ok":False,"status":"RESULT_NOT_FOUND"}
    def verify_result(self,task_id):
        item=self.store.device_task_get(task_id)
        if not item:return {"ok":False,"status":"RESULT_NOT_FOUND","verified":False}
        if item.get("status")!="COMPLETED":return {"ok":False,"status":"NOT_COMPLETED","verified":False,"task":item}
        task,result=item.get("task"),item.get("result") or {}
        if task in ("python_unittest","brain_self_test"):
            combined="\n".join((str(result.get("stdout","")),str(result.get("stderr","")))); exit_code=result.get("returncode",result.get("exit_code")); verified=exit_code in (None,0) and "Ran " in combined and "OK" in combined
        elif task=="python_version":
            stdout=str(result.get("stdout","")).strip(); exit_code=result.get("returncode",result.get("exit_code")); verified=bool(stdout) and exit_code in (None,0)
        elif task in ("brain_machine_cinema_60m","brain_machine_cinema_120m"):
            evidence=result.get("result") or result; verified=bool(result.get("ok") and evidence.get("status")=="VERIFIED_COMPLETED" and evidence.get("final"))
        else: verified=bool(item.get("ok"))
        return {"ok":verified,"verified":verified,"status":"VERIFIED" if verified else "VERIFICATION_FAILED","task_id":item["task_id"],"result":result}
    def wait_result(self,task_id,timeout=20):
        deadline=time.time()+max(.1,timeout)
        while time.time()<deadline:
            r=self.result(task_id)
            if r.get("ok") and r.get("task",{}).get("status") in ("COMPLETED","FAILED"):return r
            time.sleep(.5)
        return {"ok":False,"status":"RESULT_TIMEOUT","task_id":task_id}
    def agent_status(self):
        ttl=max(5,int(os.getenv("TERMUX_AGENT_TTL_SECONDS","15"))); now=time.time(); agents=[]
        for item in self.store.device_agents():
            age=max(0.,now-float(item.get("last_seen",0))); agents.append({"agent_id":item["agent_id"],"last_seen":item["last_seen"],"age_seconds":round(age,2),"online":age<=ttl,"state":"ONLINE" if age<=ttl else HEARTBEAT_STALE})
        return {"ttl_seconds":ttl,"online":any(x["online"] for x in agents),"agents":agents}
    def requeue_stale(self,max_age_seconds=120):
        ids=self.store.device_task_requeue_stale(max_age_seconds); return {"ok":True,"requeued":len(ids),"task_ids":ids}
    def queued_tasks(self):return self.store.device_task_counts()
    def heartbeat_age_seconds(self,agent_id):
        for item in self.store.device_agents():
            if item["agent_id"]==agent_id:return max(0.,time.time()-float(item["last_seen"]))
        return None
    def recover_stale(self):
        return self.requeue_stale(max_age_seconds=max(30,int(os.getenv("DEVICE_TASK_STALE_SECONDS","120"))))
    def status(self):
        counts=self.store.device_task_counts()
        return {"ok":True,"enabled":self.enabled(),"configured":self.configured(),"auth_env":AGENT_KEY_ENV,"auth_mode":self.auth_mode(),"queued":counts.get("QUEUED",0),"pending":counts.get("CLAIMED",0),"completed":counts.get("COMPLETED",0),"failed":counts.get("FAILED",0),"last_agent_seen":self._last_seen,"agents":self.agent_status()}

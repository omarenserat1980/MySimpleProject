"""Durable Brain-owned workflow executor with leases and event history."""
from __future__ import annotations
import json, subprocess, time, uuid
from pathlib import Path

class BrainWorkflowEngine:
    def __init__(self, root, lease_seconds=300):
        self.base=Path(root); self.root=self.base/"workflows"
        self.root.mkdir(parents=True,exist_ok=True)
        self.lease_seconds=max(5,int(lease_seconds))

    def _save(self,x):
        tmp=self.root/f".{x['id']}.tmp"
        tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(self.root/f"{x['id']}.json")

    def _event(self,x,event,**details):
        x.setdefault("events",[]).append({"event":event,"at":time.time(),**details})

    def create(self,name,command,metadata=None,cwd=None):
        metadata=metadata or {}
        idem=metadata.get("idempotency_key")
        if idem:
            for p in self.root.glob("brain-wf-*.json"):
                try:
                    old=json.loads(p.read_text(encoding="utf-8"))
                    if old.get("metadata",{}).get("idempotency_key")==idem:
                        return old
                except Exception:
                    continue
        x={"id":"brain-wf-"+uuid.uuid4().hex[:12],"name":name,"status":"QUEUED",
           "created_at":time.time(),"started_at":None,"finished_at":None,
           "heartbeat_at":None,"lease_expires_at":None,"attempt":0,"command":command,
           "metadata":metadata,"cwd":cwd,"stdout":"","stderr":"","returncode":None,"events":[]}
        self._event(x,"CREATED",attempt=0)
        self._save(x); return x

    def run(self,x):
        x["status"]="RUNNING"; x["started_at"]=time.time()
        x["attempt"]=int(x.get("attempt",0))+1
        x["heartbeat_at"]=time.time(); x["lease_expires_at"]=time.time()+self.lease_seconds
        self._event(x,"CLAIMED",attempt=x["attempt"])
        self._save(x)
        try:
            p=subprocess.run(x["command"],cwd=x.get("cwd") or None,text=True,capture_output=True,timeout=7200)
            x["stdout"]=p.stdout[-20000:]; x["stderr"]=p.stderr[-20000:]; x["returncode"]=p.returncode
            x["status"]="SUCCESS" if p.returncode==0 else "FAILED"
        except Exception as e:
            x["stderr"]=str(e); x["status"]="FAILED"; x["returncode"]=-1
        x["heartbeat_at"]=time.time(); x["lease_expires_at"]=None; x["finished_at"]=time.time()
        self._event(x,"FINISHED",status=x["status"],returncode=x["returncode"],attempt=x["attempt"])
        self._save(x); return x

    def heartbeat(self,wid):
        x=self.get(wid)
        if not x or x.get("status")!="RUNNING": return False
        x["heartbeat_at"]=time.time(); x["lease_expires_at"]=time.time()+self.lease_seconds
        self._event(x,"HEARTBEAT",attempt=x.get("attempt",0))
        self._save(x); return True

    def recover_stale(self):
        recovered=[]
        now=time.time()
        for p in self.root.glob("brain-wf-*.json"):
            try: x=json.loads(p.read_text(encoding="utf-8"))
            except Exception: continue
            if x.get("status")=="RUNNING" and float(x.get("lease_expires_at") or 0)<now:
                x["status"]="QUEUED"; x["lease_expires_at"]=None
                self._event(x,"STALE_RECOVERED",previous_attempt=x.get("attempt",0))
                self._save(x); recovered.append(x)
        return recovered

    def get(self,wid):
        p=self.root/f"{wid}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

"""Brain-owned workflow executor. No GitHub Actions dependency."""
from __future__ import annotations
import json,subprocess,time,uuid
from pathlib import Path
class BrainWorkflowEngine:
    def __init__(self,root):
        self.base=Path(root); self.root=self.base/"workflows"; self.root.mkdir(parents=True,exist_ok=True)
    def _save(self,x): (self.root/f"{x['id']}.json").write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
    def create(self,name,command,metadata=None,cwd=None):
        x={"id":"brain-wf-"+uuid.uuid4().hex[:12],"name":name,"status":"QUEUED","created_at":time.time(),"started_at":None,"finished_at":None,"command":command,"metadata":metadata or {},"cwd":cwd,"stdout":"","stderr":"","returncode":None}
        self._save(x); return x
    def run(self,x):
        x["status"]="RUNNING"; x["started_at"]=time.time(); self._save(x)
        try:
            p=subprocess.run(x["command"],cwd=x.get("cwd") or None,text=True,capture_output=True,timeout=7200)
            x["stdout"]=p.stdout[-20000:]; x["stderr"]=p.stderr[-20000:]; x["returncode"]=p.returncode
            x["status"]="SUCCESS" if p.returncode==0 else "FAILED"
        except Exception as e:
            x["stderr"]=str(e); x["status"]="FAILED"; x["returncode"]=-1
        x["finished_at"]=time.time(); self._save(x); return x
    def get(self,wid):
        p=self.root/f"{wid}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

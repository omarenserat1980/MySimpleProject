"""Dynamic director task stack with dependency-aware scheduling."""
from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json,time

@dataclass
class Task:
    task_id:str
    kind:str
    priority:int
    depends_on:list[str]
    payload:dict
    status:str="PENDING"
    attempts:int=0
    created_at:float=0.0

class TaskStack:
    def __init__(self,path="task_stack.json"):
        self.path=Path(path); self.data=self._load()
    def _load(self):
        if self.path.exists():
            try:return json.loads(self.path.read_text("utf-8"))
            except Exception:pass
        return {"tasks":{},"version":1}
    def add(self,task_id,kind,priority=50,depends_on=None,payload=None):
        if task_id in self.data["tasks"]: return self.data["tasks"][task_id]
        t=Task(task_id,kind,priority,depends_on or [],payload or {},created_at=time.time())
        self.data["tasks"][task_id]=asdict(t); self.save(); return asdict(t)
    def complete(self,task_id,status="VERIFIED"):
        if task_id in self.data["tasks"]:
            self.data["tasks"][task_id]["status"]=status; self.save()
    def next(self):
        tasks=self.data["tasks"].values()
        ready=[]
        for t in tasks:
            if t["status"] not in ("PENDING","REPAIR"): continue
            if all(self.data["tasks"].get(d,{}).get("status")=="VERIFIED" for d in t["depends_on"]):
                ready.append(t)
        return sorted(ready,key=lambda x:(-x["priority"],x["created_at"]))[0] if ready else None
    def fail(self,task_id,repair_payload=None):
        t=self.data["tasks"].get(task_id)
        if not t:return
        t["status"]="REPAIR"; t["attempts"]+=1
        if repair_payload:t["payload"]["repair"]=repair_payload
        self.save()
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),"utf-8"); tmp.replace(self.path)

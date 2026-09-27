"""Persistent continuity ledger for cinematic shot-to-shot state."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class ContinuityLedger:
    def __init__(self,path:str="cinematic_output/continuity_ledger.json"):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.data=json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"version":1,"shots":{}}
    def record(self,shot_id:str,**state:Any)->None:
        self.data["shots"][shot_id]=state
        self.path.write_text(json.dumps(self.data,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
    def previous(self,scene_id:str|None=None):
        items=list(self.data["shots"].items())
        if scene_id: items=[x for x in items if x[1].get("scene_id")==scene_id]
        return items[-1][1] if items else None
    def snapshot(self): return self.data

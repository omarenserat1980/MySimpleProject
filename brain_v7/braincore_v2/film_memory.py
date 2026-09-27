"""Persistent visual/story memory for closed-loop film generation."""
from __future__ import annotations
from pathlib import Path
import json, time
from typing import Any

class FilmMemory:
    def __init__(self,path:str="film_memory.json"):
        self.path=Path(path); self.data=self._load()
    def _load(self):
        if self.path.exists():
            try: return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception: pass
        return {"version":1,"entities":{},"shots":{},"events":[],"motifs":{},"threads":{}}
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
        tmp.replace(self.path)
    def update_shot(self,shot_id:str, evidence:dict[str,Any]):
        self.data["shots"][shot_id]=dict(evidence,updated_at=time.time())
        self.save()
    def update_entity(self,entity_id:str, state:dict[str,Any]):
        self.data["entities"].setdefault(entity_id,{}).update(state)
        self.data["entities"][entity_id]["updated_at"]=time.time()
        self.save()
    def add_event(self,event:dict[str,Any]):
        self.data["events"].append(dict(event,timestamp=time.time()))
        self.save()
    def snapshot(self): return self.data

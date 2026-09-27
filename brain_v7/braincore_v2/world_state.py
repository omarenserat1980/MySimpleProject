"""Mutable entity-centric world state used by the closed-loop film director."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, time
from typing import Any

@dataclass
class EntityState:
    entity_id:str
    kind:str
    attributes:dict[str,Any]
    evidence:list[dict[str,Any]]
    version:int=1
    updated_at:float=0.0

class WorldState:
    def __init__(self,path:str="world_state.json"):
        self.path=Path(path); self.data=self._load()
    def _load(self):
        if self.path.exists():
            try:return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:pass
        return {"version":1,"entities":{},"scene_states":{}}
    def upsert(self,entity_id:str,kind:str,attributes:dict[str,Any],evidence:dict[str,Any]|None=None):
        old=self.data["entities"].get(entity_id,{})
        item=EntityState(entity_id,kind,{**old.get("attributes",{}),**attributes},
                         old.get("evidence",[])+([evidence] if evidence else []),
                         int(old.get("version",0))+1,time.time())
        self.data["entities"][entity_id]=asdict(item); self.save(); return self.data["entities"][entity_id]
    def scene(self,scene_id:str,updates:dict[str,Any]):
        self.data["scene_states"][scene_id]={**self.data["scene_states"].get(scene_id,{}),**updates,"updated_at":time.time()}
        self.save()
    def context(self,entity_ids:list[str]|None=None)->dict[str,Any]:
        entities=self.data["entities"]
        if entity_ids is not None: entities={k:v for k,v in entities.items() if k in entity_ids}
        return {"entities":entities,"scene_states":self.data["scene_states"]}
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(self.data,ensure_ascii=False,indent=2),"utf-8"); tmp.replace(self.path)

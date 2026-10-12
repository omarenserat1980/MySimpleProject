"""Native deterministic story/project compiler for BRAIN Studio."""
from __future__ import annotations
from dataclasses import dataclass,asdict
import json,hashlib
@dataclass
class Character:
    id:str
    name:str
    role:str
    traits:list[str]
@dataclass
class Scene:
    id:str
    title:str
    duration:float
    location:str
    time_of_day:str
    characters:list[str]
    action:str
    dialogue:list[str]
def compile_story(project:dict)->dict:
    scenes=project.get("scenes",[])
    chars=project.get("characters",[])
    errors=[]
    if not project.get("title"): errors.append("missing_title")
    if not scenes: errors.append("no_scenes")
    ids={c.get("id") for c in chars}
    for s in scenes:
        if s.get("duration",0)<=0: errors.append(f"invalid_duration:{s.get('id')}")
        for c in s.get("characters",[]): 
            if c not in ids: errors.append(f"unknown_character:{c}")
    canonical=json.dumps(project,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return {"valid":not errors,"errors":errors,"sha256":hashlib.sha256(canonical.encode()).hexdigest(),"scene_count":len(scenes),"character_count":len(chars)}
if __name__=="__main__":
    import sys
    p=json.load(open(sys.argv[1],encoding="utf-8"))
    print(json.dumps(compile_story(p),ensure_ascii=False,indent=2))

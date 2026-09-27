from __future__ import annotations
import re
from .models import Shot

def decompose_script(script: str):
    blocks=[b.strip() for b in re.split(r"\n\s*\n",script) if b.strip()]
    scenes=[]
    for i,b in enumerate(blocks,1):
        first=b.splitlines()[0][:120]
        scenes.append({"scene_id":f"SC{i:04d}","location":first,"time":"",
            "characters":[],"action":" ".join(b.splitlines()),"emotion":"",
            "story_purpose":"","continuity_requirements":{}})
    return scenes

def plan_shots(scenes):
    shots=[]
    for scene in scenes:
        sid=scene["scene_id"]; chars=scene.get("characters",[])
        shots += [
            Shot(f"{sid}_001",sid,"establish geography",chars,scene["location"],scene["action"],"establishing","24mm"),
            Shot(f"{sid}_002",sid,"primary action",chars,scene["location"],scene["action"],"medium","50mm"),
            Shot(f"{sid}_003",sid,"emotional beat",chars,scene["location"],scene["action"],"close-up","85mm")
        ]
    return shots

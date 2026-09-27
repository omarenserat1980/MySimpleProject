"""Reference engine: deterministic visual identity anchors for characters and worlds."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json

def reference_id(kind:str,key:str)->str:
    return f"{kind}-{sha256(key.encode()).hexdigest()[:16]}"

def build_reference_manifest(plan:dict, output_dir:str="cinematic_output")->dict:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    chars=plan.get("character_bible",{})
    world=plan.get("world_bible",{})
    manifest={
      "version":1,
      "character_reference":{
        "reference_id":reference_id("character",json.dumps(chars,sort_keys=True)),
        "identity_lock":chars.get("face_identity",""),
        "appearance":chars.get("appearance",""),
        "wardrobe":chars.get("wardrobe",""),
        "hair":chars.get("hair",""),
        "body_language":chars.get("body_language",""),
      },
      "world_reference":{
        "reference_id":reference_id("world",json.dumps(world,sort_keys=True)),
        "geography":world.get("geography",""),
        "architecture":world.get("architecture",""),
        "era":world.get("era",""),
        "weather":world.get("weather",""),
        "time_of_day":world.get("time_of_day",""),
        "palette":world.get("palette",""),
        "props":world.get("props",[]),
      },
      "reference_policy":"Every generated shot must carry these anchors; provider-specific reference image IDs may be added later.",
    }
    path=out/"reference_manifest.json"
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return manifest

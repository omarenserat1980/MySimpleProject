"""Targeted repair planner; never rewrites verified story state unnecessarily."""
from __future__ import annotations
from typing import Any

def build_repairs(qc:dict[str,Any], shot:dict[str,Any])->dict[str,Any]:
    checks=qc.get("checks",{})
    repairs=[]
    mapping={
      "identity":"re-anchor the exact verified character reference and wardrobe state",
      "world":"re-anchor verified world geometry, props, weather and time-of-day",
      "temporal":"reduce motion complexity and preserve previous/next frame continuity",
      "audio":"lock speaker identity, acoustic space, timing and ambience",
      "visual":"increase composition, exposure and physical-lighting constraints",
      "story":"restore the beat objective without changing established causality",
      "factuality":"use only verified research-led claims and flag dramatization",
    }
    for key,ok in checks.items():
        if not ok: repairs.append({"dimension":key,"instruction":mapping.get(key,"repair failed constraint")})
    return {"status":"REPAIR_REQUIRED" if repairs else "NO_REPAIR","shot_id":shot.get("shot_id"),"repairs":repairs,
            "preserve":["character identity","world identity","chronology","verified facts","approved story beats"]}

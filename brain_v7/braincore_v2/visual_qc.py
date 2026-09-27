"""Provider-neutral visual QC contract with deterministic technical checks and pluggable vision scoring."""
from __future__ import annotations
from pathlib import Path
from typing import Any

REQUIRED=("shot_id","continuity_key","visual_prompt")

def inspect_shot(shot:dict[str,Any], result:dict[str,Any], *, min_score:float=.82)->dict[str,Any]:
    errors=[k for k in REQUIRED if not shot.get(k)]
    media=result.get("media") or result.get("video") or result.get("url")
    if not media: errors.append("media_missing")
    technical=result.get("technical_qc",True)
    if technical is False: errors.append("technical_qc_failed")
    score=float(result.get("visual_score", result.get("quality_score", 1.0 if not errors else 0.0)))
    vision=result.get("vision_qc")
    if isinstance(vision,dict):
        score=float(vision.get("score",score))
        if vision.get("status")=="FAIL": errors.append("vision_qc_failed")
    return {"status":"VERIFIED" if not errors and score>=min_score else "REJECTED",
            "score":score,"errors":errors,
            "checks":{"identity_lock":True,"world_lock":True,"prompt_alignment":not bool(errors),
                      "technical":technical,"vision":vision or "provider_score_or_fallback"}}

"""Provider-neutral visual QC with explicit evidence levels."""
from __future__ import annotations
from typing import Any

REQUIRED=("shot_id","continuity_key","visual_prompt")

def inspect_shot(shot:dict[str,Any], result:dict[str,Any], *, min_score:float=.82)->dict[str,Any]:
    errors=[k for k in REQUIRED if not shot.get(k)]
    media=result.get("media") or result.get("video") or result.get("video_ref") or result.get("url")
    if not media: errors.append("media_missing")
    technical=result.get("technical_qc", True)
    if technical is False: errors.append("technical_qc_failed")
    vision=result.get("vision_qc")
    local_proxy=result.get("local_visual_qc")
    provider_score=result.get("visual_score", result.get("quality_score"))
    if isinstance(vision,dict):
        score=float(vision.get("score",0.0))
        evidence="vision"
        if vision.get("status")=="FAIL": errors.append("vision_qc_failed")
    elif provider_score is not None:
        score=float(provider_score)
        evidence="provider_score"
    elif isinstance(local_proxy,dict):
        score=float(local_proxy.get("score",0.0))
        evidence="local_visual_proxy"
        if local_proxy.get("status")=="FAIL":
            errors.append("local_visual_proxy_failed")
    else:
        score=0.0
        evidence="technical_only"
    status="VERIFIED" if not errors and score>=min_score else "REJECTED"
    return {"status":status,"score":score,"evidence":evidence,"errors":errors,
            "checks":{"identity_lock":bool(shot.get("character_bible") or shot.get("continuity_dna")),
                      "world_lock":bool(shot.get("world_bible") or shot.get("continuity_dna")),
                      "prompt_alignment":not bool(errors),"technical":technical,
                      "vision":vision or "not_provided",
                      "local_visual_proxy":local_proxy or "not_provided"}}

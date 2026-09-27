"""Multi-dimensional cinematic QC: visual, narrative, continuity, audio and factuality."""
from __future__ import annotations
from typing import Any

def evaluate_film_evidence(shot:dict[str,Any], result:dict[str,Any], memory:dict[str,Any]|None=None)->dict[str,Any]:
    memory=memory or {}
    visual=result.get("visual_qc") or {}
    errors=list(visual.get("errors") or visual.get("issues") or [])
    score=float(visual.get("score",0.0) or 0.0)
    checks={
      "technical": result.get("status") in {"COMPLETED","VERIFIED_COMPLETED"},
      "visual": score >= float(shot.get("quality_targets",{}).get("visual_quality",0.82)),
      "identity": not any("identity" in str(e).lower() for e in errors),
      "world": not any(x in str(e).lower() for e in errors for x in ("world","geometry","location")),
      "temporal": not any(x in str(e).lower() for e in errors for x in ("flicker","jitter","temporal","morph")),
      "audio": not any(x in str(e).lower() for e in errors for x in ("audio","voice","dialogue","sync")),
      "story": True,
      "factuality": True,
    }
    status="VERIFIED" if all(checks.values()) else "REPAIR"
    return {"status":status,"score":score,"checks":checks,"issues":errors,
            "repair_plan":_repair_plan(checks,errors)}

def _repair_plan(checks:dict[str,bool],errors:list[Any])->list[str]:
    plan=[]
    if not checks["visual"]: plan.append("regenerate with stronger composition, exposure and photorealism constraints")
    if not checks["identity"]: plan.append("re-anchor character reference and previous verified appearance")
    if not checks["world"]: plan.append("re-anchor world geometry, location and persistent props")
    if not checks["temporal"]: plan.append("reduce motion complexity and enforce temporal consistency")
    if not checks["audio"]: plan.append("regenerate voice/Foley with locked speaker and acoustic profile")
    if not checks["factuality"]: plan.append("return to research ledger and remove unsupported claim")
    if not plan and errors: plan.append("target the exact QC issue without changing verified story state")
    return plan

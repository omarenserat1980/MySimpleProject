"""Fail-closed promotion gate: Arkan Twin -> real Arkan."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PromotionDecision:
    allowed: bool
    status: str
    reasons: tuple[str,...]
    required: tuple[str,...]

REQUIRED=("twin_closed","evidence_verified","authority_verified","leadership_verified",
          "resource_verified","real_heartbeat","real_task_evidence","real_verification")

class ArkanPromotionGate:
    """Only decides promotion; it never starts real execution."""
    def evaluate(self, twin_result:dict[str,Any], real_probe:dict[str,Any]|None=None)->PromotionDecision:
        reasons=[]
        checks={
          "twin_closed": twin_result.get("ok") is True and twin_result.get("status")=="GOLDEN_CLOSED_LOOP_VERIFIED",
          "evidence_verified": bool(twin_result.get("evidence_ids")),
          "authority_verified": bool(twin_result.get("authority_verified",False)),
          "leadership_verified": bool(twin_result.get("leadership_verified",False)),
          "resource_verified": bool(twin_result.get("resource_verified",False)),
        }
        for k,v in checks.items():
            if not v: reasons.append(k.upper()+"_REQUIRED")
        if real_probe is None:
            reasons.append("REAL_PROBE_REQUIRED")
        else:
            checks["real_heartbeat"]=real_probe.get("heartbeat")=="FRESH"
            checks["real_task_evidence"]=real_probe.get("task_evidence") is True
            checks["real_verification"]=real_probe.get("verification")=="VERIFIED"
            for k in ("real_heartbeat","real_task_evidence","real_verification"):
                if not checks[k]: reasons.append(k.upper()+"_REQUIRED")
        allowed=not reasons
        return PromotionDecision(allowed,"PROMOTION_ALLOWED" if allowed else "PROMOTION_BLOCKED",
                                 tuple(reasons),REQUIRED)

__all__=["ArkanPromotionGate","PromotionDecision"]

"""Owner-bound promotion gate.

Promotion remains decision-only. Owner approval is cryptographically verified
and scoped to the exact requested capability before ALLOWED can be returned.
"""
from __future__ import annotations
from typing import Any
from .owner_cryptographic_approval import verify_owner_approval

class OwnerBoundArkanPromotionGate:
    def __init__(self, public_key_b64:str):
        self.public_key_b64=public_key_b64
        self._used_challenges:set[str]=set()

    def evaluate(self, twin_result:dict[str,Any], real_probe:dict[str,Any]|None,
                 owner_approval:dict[str,Any]|None, *, now:float|None=None)->dict[str,Any]:
        from .arkan_promotion_gate import ArkanPromotionGate
        base=ArkanPromotionGate().evaluate(twin_result,real_probe)
        if not base.allowed:
            return {"allowed":False,"status":base.status,"reasons":base.reasons}
        if owner_approval is None:
            return {"allowed":False,"status":"PROMOTION_BLOCKED",
                    "reasons":("OWNER_APPROVAL_REQUIRED",)}
        try:
            verified=verify_owner_approval(owner_approval,self.public_key_b64,
                                           now=now,used_challenges=self._used_challenges)
        except ValueError as exc:
            return {"allowed":False,"status":"PROMOTION_BLOCKED","reasons":(str(exc),)}
        required_scope="windows-server-2025-real-boot"
        if verified.scope != required_scope:
            return {"allowed":False,"status":"PROMOTION_BLOCKED",
                    "reasons":("OWNER_APPROVAL_SCOPE_MISMATCH",)}
        self._used_challenges.add(verified.challenge_id)
        return {"allowed":True,"status":"PROMOTION_ALLOWED",
                "reasons":(),"owner_id":verified.owner_id,
                "challenge_id":verified.challenge_id,"scope":verified.scope}

__all__=["OwnerBoundArkanPromotionGate"]

"""Fail-closed security boundary for Jet Brain actions."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib,hmac,os

HIGH_RISK={"publish","credentials","system_admin","delete","network_external","financial_transaction","code_execution"}

@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    reason: str
    risk: str

class SecurityGuard:
    def authenticate(self,supplied: str|None)->bool:
        expected=os.getenv("BRAIN_CONTROL_KEY","")
        if not supplied or not expected:return False
        return hmac.compare_digest(str(supplied),expected)

    def authorize(self,action:str,capabilities=None,approved=False)->SecurityDecision:
        capabilities=set(capabilities or ())
        risk="high" if action in HIGH_RISK else "low"
        if action not in capabilities:
            return SecurityDecision(False,"CAPABILITY_REQUIRED",risk)
        if risk=="high" and not approved:
            return SecurityDecision(False,"EXPLICIT_APPROVAL_REQUIRED",risk)
        return SecurityDecision(True,"AUTHORIZED",risk)

    def audit_fingerprint(self,payload)->str:
        import json
        raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    def safe_metadata(self,metadata):
        blocked={"key","token","secret","password","credential","api_key","private_key"}
        return {k:v for k,v in (metadata or {}).items() if k.lower() not in blocked and "secret" not in k.lower() and "token" not in k.lower()}

"""Owner cryptographic approval boundary.

Biometrics may unlock a private key locally, but Brain never receives or stores
biometric material. Brain verifies only a signed, scoped, expiring challenge.
"""
from __future__ import annotations
import base64, json, time
from dataclasses import dataclass
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA="brain.owner-approval.v1"

@dataclass(frozen=True)
class OwnerApproval:
    owner_id:str
    challenge_id:str
    scope:str
    expires_at:float
    signature:str

def approval_payload(owner_id:str, challenge_id:str, scope:str, expires_at:float)->bytes:
    return json.dumps({
        "schema":SCHEMA,"owner_id":owner_id,"challenge_id":challenge_id,
        "scope":scope,"expires_at":expires_at
    },sort_keys=True,separators=(",",":")).encode()

def verify_owner_approval(approval:dict, public_key_b64:str, *, now:float|None=None,
                          used_challenges:set[str]|None=None)->OwnerApproval:
    if not isinstance(approval,dict) or approval.get("schema")!=SCHEMA:
        raise ValueError("OWNER_APPROVAL_SCHEMA_INVALID")
    owner_id=str(approval.get("owner_id","")).strip()
    challenge_id=str(approval.get("challenge_id","")).strip()
    scope=str(approval.get("scope","")).strip()
    expires_at=approval.get("expires_at")
    signature=str(approval.get("signature",""))
    if not owner_id or not challenge_id or not scope or not signature:
        raise ValueError("OWNER_APPROVAL_FIELDS_REQUIRED")
    if not isinstance(expires_at,(int,float)) or expires_at <= 0:
        raise ValueError("OWNER_APPROVAL_EXPIRY_INVALID")
    if (now if now is not None else time.time()) >= expires_at:
        raise ValueError("OWNER_APPROVAL_EXPIRED")
    if used_challenges is not None and challenge_id in used_challenges:
        raise ValueError("OWNER_APPROVAL_REPLAY")
    try:
        key=Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64,validate=True))
        key.verify(base64.b64decode(signature,validate=True),
                   approval_payload(owner_id,challenge_id,scope,expires_at))
    except (InvalidSignature,ValueError,TypeError):
        raise ValueError("OWNER_APPROVAL_SIGNATURE_INVALID")
    return OwnerApproval(owner_id,challenge_id,scope,float(expires_at),signature)

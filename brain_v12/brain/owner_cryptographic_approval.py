"""Owner cryptographic approval boundary.

Approvals are signed for one exact commit/task/attempt. Brain never receives or
stores biometric material; only the scoped, expiring Ed25519 approval is verified.
"""
from __future__ import annotations
import base64, json, time
from dataclasses import dataclass
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA="brain.owner-approval.v2"

@dataclass(frozen=True)
class OwnerApproval:
    owner_id:str
    challenge_id:str
    scope:str
    expires_at:float
    signature:str
    source_commit:str
    task_id:str
    attempt_id:str

def approval_payload(owner_id:str, challenge_id:str, scope:str, expires_at:float,
                     source_commit:str, task_id:str, attempt_id:str)->bytes:
    return json.dumps({
        "schema":SCHEMA,"owner_id":owner_id,"challenge_id":challenge_id,
        "scope":scope,"expires_at":expires_at,"source_commit":source_commit,
        "task_id":task_id,"attempt_id":attempt_id
    },sort_keys=True,separators=(",",":")).encode()

def verify_owner_approval(approval:dict, public_key_b64:str, *, now:float|None=None,
                          used_challenges:set[str]|None=None, source_commit:str|None=None,
                          task_id:str|None=None, attempt_id:str|None=None)->OwnerApproval:
    if not isinstance(approval,dict) or approval.get("schema")!=SCHEMA:
        raise ValueError("OWNER_APPROVAL_SCHEMA_INVALID")
    owner_id=str(approval.get("owner_id","")).strip()
    challenge_id=str(approval.get("challenge_id","")).strip()
    scope=str(approval.get("scope","")).strip()
    signed_commit=str(approval.get("source_commit","")).strip().lower()
    signed_task=str(approval.get("task_id","")).strip()
    signed_attempt=str(approval.get("attempt_id","")).strip()
    expires_at=approval.get("expires_at")
    signature=str(approval.get("signature",""))
    if not all((owner_id,challenge_id,scope,signature,signed_commit,signed_task,signed_attempt)):
        raise ValueError("OWNER_APPROVAL_FIELDS_REQUIRED")
    if len(signed_commit)!=40 or any(c not in "0123456789abcdef" for c in signed_commit):
        raise ValueError("OWNER_APPROVAL_SOURCE_COMMIT_INVALID")
    if not isinstance(expires_at,(int,float)) or expires_at <= 0:
        raise ValueError("OWNER_APPROVAL_EXPIRY_INVALID")
    if (now if now is not None else time.time()) >= expires_at:
        raise ValueError("OWNER_APPROVAL_EXPIRED")
    if used_challenges is not None and challenge_id in used_challenges:
        raise ValueError("OWNER_APPROVAL_REPLAY")
    if source_commit is not None and signed_commit != str(source_commit).strip().lower():
        raise ValueError("OWNER_APPROVAL_SOURCE_COMMIT_MISMATCH")
    if task_id is not None and signed_task != str(task_id).strip():
        raise ValueError("OWNER_APPROVAL_TASK_MISMATCH")
    if attempt_id is not None and signed_attempt != str(attempt_id).strip():
        raise ValueError("OWNER_APPROVAL_ATTEMPT_MISMATCH")
    try:
        key=Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64,validate=True))
        key.verify(base64.b64decode(signature,validate=True),
                   approval_payload(owner_id,challenge_id,scope,expires_at,signed_commit,signed_task,signed_attempt))
    except (InvalidSignature,ValueError,TypeError):
        raise ValueError("OWNER_APPROVAL_SIGNATURE_INVALID")
    return OwnerApproval(owner_id,challenge_id,scope,float(expires_at),signature,signed_commit,signed_task,signed_attempt)

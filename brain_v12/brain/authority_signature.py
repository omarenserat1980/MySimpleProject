"""Asymmetric Brain authority signatures for portable execution contracts.

Private signing material stays in the Brain Control Plane. Executors only need
the public verification key.
"""
from __future__ import annotations
import base64, json, os
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

ALGORITHM="Ed25519"
_FIELDS=("brain_id","generation","fencing_token","lease_id","holder_id","task_id","attempt_id",
         "source_commit","checkpoint_source_commit","capability","executor","authority_policy_version","authority_decision")

def signing_payload(contract:dict)->bytes:
    fields={k:contract.get(k) for k in _FIELDS}
    return json.dumps(fields,sort_keys=True,separators=(",",":")).encode()

def _b64(value:str)->bytes:
    return base64.b64decode(value.encode(),validate=True)

def sign_contract(contract:dict, private_key_b64:str|None=None)->str:
    raw=private_key_b64 or os.environ.get("BRAIN_AUTHORITY_PRIVATE_KEY_B64","")
    if not raw: raise RuntimeError("BRAIN_AUTHORITY_PRIVATE_KEY_REQUIRED")
    try: key=Ed25519PrivateKey.from_private_bytes(_b64(raw))
    except Exception as exc: raise RuntimeError("BRAIN_AUTHORITY_PRIVATE_KEY_INVALID") from exc
    return base64.b64encode(key.sign(signing_payload(contract))).decode()

def verify_contract_signature(contract:dict, signature:str, public_key_b64:str|None=None)->bool:
    raw=public_key_b64 or os.environ.get("BRAIN_AUTHORITY_PUBLIC_KEY_B64","")
    if not raw: raise RuntimeError("BRAIN_AUTHORITY_PUBLIC_KEY_REQUIRED")
    if contract.get("authority_signature_algorithm")!=ALGORITHM: return False
    try:
        key=Ed25519PublicKey.from_public_bytes(_b64(raw))
        key.verify(base64.b64decode(str(signature).encode(),validate=True),signing_payload(contract))
        return True
    except (InvalidSignature,ValueError,TypeError,Exception) as exc:
        if isinstance(exc,RuntimeError): raise
        return False

"""Secure enrollment primitives for BRAIN Cloud Fabric.

The control plane stores only a hash of the enrollment token. Raw tokens are
returned once by the enrollment operation and should be delivered over an
already-authenticated administrative channel.
"""
from __future__ import annotations
import hashlib, hmac, os, secrets, time
from pathlib import Path

def _root() -> Path:
    p=Path(os.getenv("BRAIN_FABRIC_STATE_DIR", ".brain_state/fabric"))
    p.mkdir(parents=True, exist_ok=True)
    return p

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_enrollment(node_id: str, ttl_seconds: int = 900) -> dict:
    if not node_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in node_id):
        raise ValueError("invalid node_id")
    if ttl_seconds < 60 or ttl_seconds > 86400:
        raise ValueError("ttl_seconds must be between 60 and 86400")
    token=secrets.token_urlsafe(32)
    record={
        "node_id": node_id,
        "token_hash": _hash(token),
        "expires_at": time.time()+ttl_seconds,
        "used": False,
    }
    ( _root()/f"enrollment-{node_id}.json").write_text(__import__("json").dumps(record),encoding="utf-8")
    return {"node_id":node_id,"enrollment_token":token,"expires_at":record["expires_at"]}

def verify_enrollment(node_id: str, token: str) -> bool:
    path=_root()/f"enrollment-{node_id}.json"
    if not path.exists():
        return False
    try:
        record=__import__("json").loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if record.get("used") or float(record.get("expires_at",0)) < time.time():
        return False
    return hmac.compare_digest(str(record.get("token_hash","")), _hash(token))

def consume_enrollment(node_id: str, token: str) -> bool:
    if not verify_enrollment(node_id, token):
        return False
    path=_root()/f"enrollment-{node_id}.json"
    record=__import__("json").loads(path.read_text(encoding="utf-8"))
    record["used"]=True
    path.write_text(__import__("json").dumps(record),encoding="utf-8")
    return True

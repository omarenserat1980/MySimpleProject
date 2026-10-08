"""Fail-closed Brain identity and recovery-generation contract.

Identity is public metadata only. No private key, token, password, or device
secret is stored here. A recovered runtime must present a valid identity
document and a monotonic generation before it can claim current authority.
"""
from __future__ import annotations
from typing import Any

IDENTITY_SCHEMA = "brain.identity.v1"

def validate_identity(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("BRAIN_IDENTITY_INVALID")
    if data.get("schema") != IDENTITY_SCHEMA:
        raise ValueError("BRAIN_IDENTITY_SCHEMA_INVALID")
    brain_id = str(data.get("brain_id", "")).strip()
    source_commit = str(data.get("source_commit", "")).strip().lower()
    checkpoint_id = str(data.get("checkpoint_id", "")).strip()
    generation = data.get("generation")
    if not brain_id:
        raise ValueError("BRAIN_IDENTITY_ID_REQUIRED")
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
        raise ValueError("BRAIN_IDENTITY_GENERATION_INVALID")
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("BRAIN_IDENTITY_SOURCE_COMMIT_INVALID")
    if not checkpoint_id:
        raise ValueError("BRAIN_IDENTITY_CHECKPOINT_REQUIRED")
    return {"verified": True, "schema": IDENTITY_SCHEMA, "brain_id": brain_id,
            "generation": generation, "source_commit": source_commit,
            "checkpoint_id": checkpoint_id}

def require_newer_generation(identity: dict[str, Any], previous_generation: int) -> dict[str, Any]:
    verified = validate_identity(identity)
    if verified["generation"] <= int(previous_generation):
        raise RuntimeError("BRAIN_IDENTITY_GENERATION_NOT_NEWER")
    return verified

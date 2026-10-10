"""Verify signed Brain Cloud Executor attestations.

The trust anchor (Ed25519 public key) is provisioned out-of-band on the host.
The attestation document is signed by the trusted issuer, not by the runner
bootstrap itself. Never generate production signing keys in CI.
"""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "brain.cloud-executor-attestation.v1"
AUDIENCE = "brain-cloud-executor"
MAX_VALIDITY_SECONDS = 3600
MAX_CLOCK_SKEW_SECONDS = 120


def signing_payload(document: dict[str, Any]) -> bytes:
    """Canonical payload: all fields except signature."""
    payload = {key: value for key, value in document.items() if key != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_attestation(
    attestation_file: str,
    public_key_b64: str,
    expected_executor_id: str,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Validate issuer signature, executor binding, audience, and short validity."""
    if not attestation_file:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_FILE_REQUIRED")
    if not public_key_b64:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_TRUST_KEY_REQUIRED")
    if not expected_executor_id.strip():
        raise ValueError("CLOUD_EXECUTOR_ID_REQUIRED")
    path = Path(attestation_file)
    if not path.is_file():
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_FILE_MISSING")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_DOCUMENT_INVALID") from exc
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_SCHEMA_INVALID")

    required = ("executor_id", "audience", "issued_at", "expires_at", "nonce", "signature")
    if any(key not in document for key in required):
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_FIELDS_REQUIRED")
    if document["executor_id"] != expected_executor_id:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_EXECUTOR_MISMATCH")
    if document["audience"] != AUDIENCE:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_AUDIENCE_MISMATCH")
    if not isinstance(document["nonce"], str) or len(document["nonce"].strip()) < 16:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_NONCE_INVALID")
    if isinstance(document["issued_at"], bool) or not isinstance(document["issued_at"], (int, float)):
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_ISSUED_AT_INVALID")
    if isinstance(document["expires_at"], bool) or not isinstance(document["expires_at"], (int, float)):
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_EXPIRY_INVALID")

    current = time.time() if now is None else float(now)
    issued_at = float(document["issued_at"])
    expires_at = float(document["expires_at"])
    if issued_at > current + MAX_CLOCK_SKEW_SECONDS:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_NOT_YET_VALID")
    if expires_at <= current:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_EXPIRED")
    if expires_at <= issued_at or expires_at - issued_at > MAX_VALIDITY_SECONDS:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_VALIDITY_INVALID")

    try:
        key_bytes = base64.b64decode(public_key_b64, validate=True)
        key = Ed25519PublicKey.from_public_bytes(key_bytes)
        signature = base64.b64decode(str(document["signature"]), validate=True)
        key.verify(signature, signing_payload(document))
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_SIGNATURE_INVALID") from exc

    return {
        "verified": True,
        "schema": SCHEMA,
        "executor_id": expected_executor_id,
        "audience": AUDIENCE,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": document["nonce"],
    }


def verify_from_environment(expected_executor_id: str, *, now: float | None = None) -> dict[str, Any]:
    """Verify host-provisioned attestation using a host-provisioned trust anchor."""
    return verify_attestation(
        os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE", ""),
        os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64", ""),
        expected_executor_id,
        now=now,
    )

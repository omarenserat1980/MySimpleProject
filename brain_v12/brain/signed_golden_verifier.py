"""Cryptographic attestation for real Golden Acceptance verification records.

Only the trusted verifier holds the private key. Brain receives the Ed25519
public key through an out-of-band deployment setting and rejects unsigned,
expired, mis-scoped, or replayed attestations.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "brain.golden-verifier-attestation.v1"
AUDIENCE = "brain-golden-acceptance"
MAX_VALIDITY_SECONDS = 300


def signing_payload(document: dict[str, Any]) -> bytes:
    return json.dumps(
        {key: value for key, value in document.items() if key != "signature"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def verify_signed_verification(
    attestation: dict[str, Any],
    *,
    public_key_b64: str | None = None,
    now: float | None = None,
    replay_db_path: str | Path | None = None,
    expected: dict[str, Any],
) -> dict[str, Any]:
    """Verify a signed verifier statement against the exact acceptance scope."""
    key_text = public_key_b64 if public_key_b64 is not None else os.environ.get(
        "BRAIN_GOLDEN_VERIFIER_PUBLIC_KEY_B64", ""
    )
    if not key_text:
        raise ValueError("GOLDEN_VERIFIER_TRUST_KEY_REQUIRED")
    if not isinstance(attestation, dict):
        raise ValueError("GOLDEN_VERIFIER_ATTESTATION_INVALID")

    required = {
        "schema", "audience", "verifier_id", "task_id", "mission_id", "attempt",
        "reality_level", "verified", "evidence_ids", "criterion_ids",
        "issued_at", "expires_at", "nonce", "signature",
    }
    if not required.issubset(attestation):
        raise ValueError("GOLDEN_VERIFIER_ATTESTATION_FIELDS_REQUIRED")
    if attestation["schema"] != SCHEMA:
        raise ValueError("GOLDEN_VERIFIER_ATTESTATION_SCHEMA_INVALID")
    if attestation["audience"] != AUDIENCE:
        raise ValueError("GOLDEN_VERIFIER_ATTESTATION_AUDIENCE_MISMATCH")
    if not isinstance(attestation["verifier_id"], str) or not attestation["verifier_id"].strip():
        raise ValueError("GOLDEN_VERIFIER_ID_REQUIRED")
    if attestation["verified"] is not True:
        raise ValueError("GOLDEN_VERIFIER_DID_NOT_VERIFY")

    for field in ("task_id", "mission_id", "attempt", "reality_level", "evidence_ids", "criterion_ids"):
        if attestation[field] != expected[field]:
            raise ValueError("GOLDEN_VERIFIER_SCOPE_MISMATCH:" + field)

    issued_at = attestation["issued_at"]
    expires_at = attestation["expires_at"]
    if isinstance(issued_at, bool) or not isinstance(issued_at, (int, float)):
        raise ValueError("GOLDEN_VERIFIER_ISSUED_AT_INVALID")
    if isinstance(expires_at, bool) or not isinstance(expires_at, (int, float)):
        raise ValueError("GOLDEN_VERIFIER_EXPIRY_INVALID")
    current = time.time() if now is None else float(now)
    if issued_at > current + 60:
        raise ValueError("GOLDEN_VERIFIER_NOT_YET_VALID")
    if expires_at <= current:
        raise ValueError("GOLDEN_VERIFIER_EXPIRED")
    if expires_at <= issued_at or expires_at - issued_at > MAX_VALIDITY_SECONDS:
        raise ValueError("GOLDEN_VERIFIER_VALIDITY_INVALID")
    nonce = attestation["nonce"]
    if not isinstance(nonce, str) or len(nonce.strip()) < 16:
        raise ValueError("GOLDEN_VERIFIER_NONCE_INVALID")

    try:
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(key_text, validate=True))
        signature = base64.b64decode(str(attestation["signature"]), validate=True)
        key.verify(signature, signing_payload(attestation))
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise ValueError("GOLDEN_VERIFIER_SIGNATURE_INVALID") from exc

    if replay_db_path is not None:
        path = Path(replay_db_path)
        if path.is_symlink():
            raise ValueError("GOLDEN_VERIFIER_REPLAY_STORE_SYMLINK_REJECTED")
        if not path.parent.is_dir():
            raise ValueError("GOLDEN_VERIFIER_REPLAY_STORE_REQUIRED")
        try:
            with sqlite3.connect(str(path), timeout=5, isolation_level=None) as db:
                db.execute("PRAGMA busy_timeout=5000")
                db.execute(
                    "CREATE TABLE IF NOT EXISTS golden_verifier_nonces "
                    "(nonce TEXT PRIMARY KEY, verifier_id TEXT NOT NULL, expires_at REAL NOT NULL, consumed_at REAL NOT NULL)"
                )
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM golden_verifier_nonces WHERE expires_at <= ?", (current,))
                try:
                    db.execute(
                        "INSERT INTO golden_verifier_nonces VALUES (?, ?, ?, ?)",
                        (nonce, attestation["verifier_id"], float(expires_at), current),
                    )
                except sqlite3.IntegrityError as exc:
                    db.execute("ROLLBACK")
                    raise ValueError("GOLDEN_VERIFIER_REPLAY_DETECTED") from exc
                db.execute("COMMIT")
        except sqlite3.Error as exc:
            raise ValueError("GOLDEN_VERIFIER_REPLAY_STORE_UNAVAILABLE") from exc

    return {
        "verified": True,
        "verifier_id": attestation["verifier_id"],
        "nonce": nonce,
        "expires_at": float(expires_at),
    }

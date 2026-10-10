
"""Control-plane-only Ed25519 attestation issuer.

Only call behind an authenticated Brain control-plane adapter. The adapter
must authenticate the executor before challenge creation and signing.
"""
from __future__ import annotations
import base64, os, secrets, sqlite3, time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .cloud_executor_attestation import AUDIENCE, MAX_VALIDITY_SECONDS, SCHEMA, signing_payload

CHALLENGE_TTL_SECONDS = 60

def _connect(db_path: str):
    if not db_path or Path(db_path).is_symlink():
        raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_STORE_INVALID")
    path = Path(db_path)
    if not path.parent.is_dir():
        raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_STORE_PARENT_MISSING")
    db = sqlite3.connect(str(path), timeout=5, isolation_level=None)
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("CREATE TABLE IF NOT EXISTS issued_challenges (nonce TEXT PRIMARY KEY, executor_id TEXT NOT NULL, expires_at REAL NOT NULL, consumed_at REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS issued_attestations (nonce TEXT PRIMARY KEY, executor_id TEXT NOT NULL, expires_at REAL NOT NULL, consumed_at REAL)")
    return db

@contextmanager
def _connection(db_path: str):
    db = _connect(db_path)
    try:
        yield db
    finally:
        db.close()

def create_challenge(*, authenticated_executor_id: str, challenge_db_path: str, now: float | None = None) -> dict[str, Any]:
    executor_id = authenticated_executor_id.strip()
    if not executor_id:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_EXECUTOR_ID_REQUIRED")
    hostname = expected_hostname.strip()
    architecture = expected_architecture.strip().lower()
    architecture = "x86_64" if architecture in {"x86_64", "amd64"} else architecture
    if not hostname:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_HOSTNAME_REQUIRED")
    if architecture != "x86_64":
        raise ValueError("CLOUD_EXECUTOR_ISSUER_ARCHITECTURE_INVALID")
    current = time.time() if now is None else float(now)
    nonce = secrets.token_urlsafe(32)
    expires_at = current + CHALLENGE_TTL_SECONDS
    try:
        with _connection(challenge_db_path) as db:
            db.execute("INSERT INTO issued_challenges VALUES (?, ?, ?, NULL)", (nonce, executor_id, expires_at))
    except sqlite3.Error as exc:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_STORE_UNAVAILABLE") from exc
    return {"nonce": nonce, "expires_at": expires_at, "executor_id": executor_id}

def _consume_challenge(db_path: str, executor_id: str, nonce: str, now: float) -> None:
    try:
        with _connect(db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT executor_id, expires_at, consumed_at FROM issued_challenges WHERE nonce=?", (nonce,)).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_UNKNOWN")
            if row[0] != executor_id:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_EXECUTOR_MISMATCH")
            if row[2] is not None:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_REPLAY")
            if row[1] <= now:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_EXPIRED")
            db.execute("UPDATE issued_challenges SET consumed_at=? WHERE nonce=? AND consumed_at IS NULL", (now, nonce))
            db.execute("COMMIT")
    except sqlite3.Error as exc:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_CHALLENGE_STORE_UNAVAILABLE") from exc

def issue_attestation(*, authenticated_executor_id: str, challenge_nonce: str, challenge_db_path: str, expected_hostname: str, expected_architecture: str, lifetime_seconds: int = 300, issued_at: float | None = None, private_key_b64: str | None = None) -> dict[str, Any]:
    executor_id, nonce = authenticated_executor_id.strip(), challenge_nonce.strip()
    if not executor_id:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_EXECUTOR_ID_REQUIRED")
    if isinstance(lifetime_seconds, bool) or not 1 <= lifetime_seconds <= min(300, MAX_VALIDITY_SECONDS):
        raise ValueError("CLOUD_EXECUTOR_ISSUER_LIFETIME_INVALID")
    raw = private_key_b64 or os.environ.get("BRAIN_EXECUTOR_ATTESTATION_SIGNING_KEY_B64", "")
    if not raw:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_SIGNING_KEY_REQUIRED")
    try:
        key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw, validate=True))
    except Exception as exc:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_SIGNING_KEY_INVALID") from exc
    current = time.time() if issued_at is None else float(issued_at)
    _consume_challenge(challenge_db_path, executor_id, nonce, current)
    document = {"schema": SCHEMA, "executor_id": executor_id, "audience": AUDIENCE,
                "hostname": hostname, "architecture": architecture,
                "issued_at": current, "expires_at": current + lifetime_seconds, "nonce": nonce}
    document["signature"] = base64.b64encode(key.sign(signing_payload(document))).decode("ascii")
    try:
        with _connect(challenge_db_path) as db:
            db.execute("INSERT INTO issued_attestations VALUES (?, ?, ?, NULL)",
                       (nonce, executor_id, document["expires_at"]))
    except sqlite3.Error as exc:
        raise ValueError("CLOUD_EXECUTOR_ISSUER_ATTESTATION_REGISTRY_UNAVAILABLE") from exc
    return document

def consume_issued_attestation(*, authenticated_executor_id: str, nonce: str, registry_db_path: str, now: float | None = None) -> dict[str, Any]:
    """Atomically consume an issued attestation nonce in the central registry."""
    executor_id, nonce = authenticated_executor_id.strip(), nonce.strip()
    if not executor_id or not nonce:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_CONSUME_FIELDS_REQUIRED")
    current = time.time() if now is None else float(now)
    try:
        with _connection(registry_db_path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT executor_id, expires_at, consumed_at FROM issued_attestations WHERE nonce=?", (nonce,)).fetchone()
            if row is None:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ATTESTATION_NOT_ISSUED_BY_REGISTRY")
            if row[0] != executor_id:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ATTESTATION_EXECUTOR_MISMATCH")
            if row[1] <= current:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ATTESTATION_EXPIRED")
            if row[2] is not None:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ATTESTATION_REPLAY_DETECTED")
            db.execute("UPDATE issued_attestations SET consumed_at=? WHERE nonce=? AND consumed_at IS NULL", (current, nonce))
            db.execute("COMMIT")
    except sqlite3.Error as exc:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_REGISTRY_UNAVAILABLE") from exc
    return {"consumed": True, "executor_id": executor_id, "expires_at": float(row[1])}

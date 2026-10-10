"""Verify signed Brain Cloud Executor attestations.

The trust anchor (Ed25519 public key) is provisioned out-of-band on the host.
The attestation document is signed by the trusted issuer, not by the runner
bootstrap itself. Never generate production signing keys in CI.
"""
from __future__ import annotations

import base64
import json
import os
import platform
import socket
import sqlite3
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "brain.cloud-executor-attestation.v2"
AUDIENCE = "brain-cloud-executor"
MAX_VALIDITY_SECONDS = 300
MAX_CLOCK_SKEW_SECONDS = 120
DEFAULT_REPLAY_DB = "/var/lib/brain/cloud-executor-attestation-nonces.sqlite3"


def _consume_nonce(db_path: str, nonce: str, executor_id: str, expires_at: float, now: float) -> None:
    path = Path(db_path)
    if not db_path or not path.parent.is_dir():
        raise ValueError("CLOUD_EXECUTOR_REPLAY_STORE_REQUIRED")
    if path.is_symlink():
        raise ValueError("CLOUD_EXECUTOR_REPLAY_STORE_SYMLINK_REJECTED")
    try:
        with sqlite3.connect(str(path), timeout=5, isolation_level=None) as db:
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("CREATE TABLE IF NOT EXISTS consumed_nonces (nonce TEXT PRIMARY KEY, executor_id TEXT NOT NULL, expires_at REAL NOT NULL, consumed_at REAL NOT NULL)")
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM consumed_nonces WHERE expires_at <= ?", (now,))
            try:
                db.execute("INSERT INTO consumed_nonces VALUES (?, ?, ?, ?)", (nonce, executor_id, expires_at, now))
            except sqlite3.IntegrityError as exc:
                db.execute("ROLLBACK")
                raise ValueError("CLOUD_EXECUTOR_ATTESTATION_REPLAY_DETECTED") from exc
            db.execute("COMMIT")
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    except sqlite3.Error as exc:
        raise ValueError("CLOUD_EXECUTOR_REPLAY_STORE_UNAVAILABLE") from exc


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
    replay_db_path: str | None = None,
    expected_hostname: str | None = None,
    expected_architecture: str | None = None,
) -> dict[str, Any]:
    """Validate issuer signature and optionally consume its nonce atomically."""
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

    required = ("executor_id", "audience", "hostname", "architecture", "issued_at", "expires_at", "nonce", "signature")
    if any(key not in document for key in required):
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_FIELDS_REQUIRED")
    if document["executor_id"] != expected_executor_id:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_EXECUTOR_MISMATCH")
    if document["audience"] != AUDIENCE:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_AUDIENCE_MISMATCH")
    actual_hostname = socket.gethostname()
    actual_arch = platform.machine().lower()
    actual_arch = "x86_64" if actual_arch in {"x86_64", "amd64"} else actual_arch
    wanted_hostname = actual_hostname if expected_hostname is None else expected_hostname
    wanted_arch = actual_arch if expected_architecture is None else expected_architecture.lower()
    wanted_arch = "x86_64" if wanted_arch in {"x86_64", "amd64"} else wanted_arch
    if not isinstance(document["hostname"], str) or not document["hostname"].strip():
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_HOSTNAME_INVALID")
    if not isinstance(document["architecture"], str) or document["architecture"] != "x86_64":
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_ARCHITECTURE_INVALID")
    if not wanted_hostname or document["hostname"] != wanted_hostname:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_HOSTNAME_MISMATCH")
    if wanted_arch != "x86_64" or document["architecture"] != wanted_arch:
        raise ValueError("CLOUD_EXECUTOR_ATTESTATION_ARCHITECTURE_MISMATCH")
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

    if replay_db_path is not None:
        _consume_nonce(replay_db_path, document["nonce"], expected_executor_id, expires_at, current)

    return {
        "verified": True,
        "schema": SCHEMA,
        "executor_id": expected_executor_id,
        "audience": AUDIENCE,
        "hostname": document["hostname"],
        "architecture": document["architecture"],
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": document["nonce"],
    }


def verify_from_environment(expected_executor_id: str, *, now: float | None = None) -> dict[str, Any]:
    """Verify host-provisioned attestation using a host-provisioned trust anchor."""
    result = verify_attestation(
        os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_FILE", ""),
        os.environ.get("BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64", ""),
        expected_executor_id,
        now=now,
        replay_db_path=None,
    )
    registry_url = os.environ.get("BRAIN_CLOUD_EXECUTOR_REGISTRY_URL", "").rstrip("/")
    token = os.environ.get("BRAIN_CLOUD_EXECUTOR_TOKEN", "")
    if not registry_url or not token:
        raise ValueError("CLOUD_EXECUTOR_CENTRAL_REGISTRY_CONFIGURATION_REQUIRED")
    if not registry_url.startswith("https://"):
        raise ValueError("CLOUD_EXECUTOR_CENTRAL_REGISTRY_HTTPS_REQUIRED")
    body = json.dumps({"executor_id": expected_executor_id, "nonce": result["nonce"]}).encode("utf-8")
    request = urllib.request.Request(
        registry_url + "/api/cloud-executor/attestation/consume",
        data=body,
        headers={"Content-Type": "application/json", "X-Brain-Executor-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            registry_result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise ValueError("CLOUD_EXECUTOR_CENTRAL_REGISTRY_UNAVAILABLE") from exc
    if not isinstance(registry_result, dict) or registry_result.get("consumed") is not True:
        raise ValueError("CLOUD_EXECUTOR_CENTRAL_REGISTRY_REJECTED")
    return result

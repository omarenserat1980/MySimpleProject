#!/usr/bin/env python3
"""Fail-closed verifier for Brain Phone Base challenge-response proofs.

This verifies signatures and binding fields, not hardware-backed identity.
The verifier key must be pinned out-of-band and the device key must come from
trusted enrollment/attestation, never solely from the response.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

CHALLENGE_SCHEMA = "brain-phone-base.identity-challenge.v1"
RESPONSE_SCHEMA = "brain-phone-base.identity-response.v1"
MAX_CHALLENGE_TTL = timedelta(minutes=5)


class VerificationError(ValueError):
    """A fail-closed challenge/response validation error."""


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise VerificationError(f"INVALID_TIME:{field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationError(f"INVALID_TIME:{field}") from exc
    if parsed.tzinfo is None:
        raise VerificationError(f"TIMEZONE_REQUIRED:{field}")
    return parsed.astimezone(timezone.utc)


def _load_public_key(pem: bytes):
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey, SECP256R1
    except ImportError as exc:
        raise VerificationError("CRYPTO_BACKEND_UNAVAILABLE") from exc
    try:
        key = serialization.load_pem_public_key(pem)
    except (ValueError, TypeError) as exc:
        raise VerificationError("PUBLIC_KEY_INVALID") from exc
    if isinstance(key, Ed25519PublicKey):
        return key
    if isinstance(key, EllipticCurvePublicKey) and isinstance(key.curve, SECP256R1):
        return key
    raise VerificationError("SUPPORTED_KEY_REQUIRED:Ed25519_or_P256")


def public_key_id(public_key_pem: bytes) -> str:
    """Fingerprint the canonical SubjectPublicKeyInfo DER for a supported key."""
    from cryptography.hazmat.primitives import serialization
    key = _load_public_key(public_key_pem)
    der = key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return sha256_hex(der)


def _verify_signature(public_key_pem: bytes, signature_b64: str, message: bytes) -> None:
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError as exc:
        raise VerificationError("CRYPTO_BACKEND_UNAVAILABLE") from exc
    key = _load_public_key(public_key_pem)
    if not isinstance(signature_b64, str):
        raise VerificationError("SIGNATURE_MISSING")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise VerificationError("SIGNATURE_ENCODING_INVALID") from exc
    try:
        if isinstance(key, ec.EllipticCurvePublicKey):
            key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        else:
            key.verify(signature, message)
    except Exception as exc:
        raise VerificationError("SIGNATURE_INVALID") from exc


def verify_challenge_response(
    *,
    challenge: dict[str, Any],
    challenge_signature_b64: str,
    pinned_verifier_public_key_pem: bytes,
    response: dict[str, Any],
    response_signature_b64: str,
    enrolled_device_public_key_pem: bytes,
    expected_measurement_sha256: str,
    now: datetime | None = None,
    seen_challenge_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Verify a signed fresh challenge and a response bound to one measurement.

    The verifier key is pinned out-of-band. The device public key must be
    obtained from a separately trusted enrollment/attestation source.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if challenge.get("schema") != CHALLENGE_SCHEMA:
        raise VerificationError("CHALLENGE_SCHEMA_INVALID")
    if response.get("schema") != RESPONSE_SCHEMA:
        raise VerificationError("RESPONSE_SCHEMA_INVALID")

    challenge_id = challenge.get("challenge_id")
    nonce = challenge.get("nonce")
    key_id = challenge.get("device_key_id")
    measurement_hash = challenge.get("measurement_sha256")
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        raise VerificationError("CHALLENGE_ID_INVALID")
    if seen_challenge_ids is not None and challenge_id in seen_challenge_ids:
        raise VerificationError("CHALLENGE_REPLAYED")
    if not isinstance(nonce, str):
        raise VerificationError("NONCE_INVALID")
    try:
        nonce_bytes = bytes.fromhex(nonce)
    except ValueError as exc:
        raise VerificationError("NONCE_INVALID") from exc
    if len(nonce_bytes) < 32:
        raise VerificationError("NONCE_TOO_SHORT")
    if not isinstance(measurement_hash, str) or len(measurement_hash) != 64:
        raise VerificationError("MEASUREMENT_HASH_INVALID")
    try:
        int(measurement_hash, 16)
    except ValueError as exc:
        raise VerificationError("MEASUREMENT_HASH_INVALID") from exc
    if measurement_hash != expected_measurement_sha256:
        raise VerificationError("MEASUREMENT_HASH_MISMATCH")

    issued = _parse_time(challenge.get("issued_at_utc"), "issued_at_utc")
    expires = _parse_time(challenge.get("expires_at_utc"), "expires_at_utc")
    if expires <= issued or expires - issued > MAX_CHALLENGE_TTL:
        raise VerificationError("CHALLENGE_TTL_INVALID")
    if issued > current + timedelta(seconds=30):
        raise VerificationError("CHALLENGE_FROM_FUTURE")
    if current >= expires:
        raise VerificationError("CHALLENGE_EXPIRED")

    _verify_signature(pinned_verifier_public_key_pem, challenge_signature_b64, canonical_json(challenge))
    if key_id != public_key_id(enrolled_device_public_key_pem):
        raise VerificationError("DEVICE_KEY_ID_MISMATCH")

    expected_fields = {
        "schema": RESPONSE_SCHEMA,
        "challenge_id": challenge_id,
        "nonce": nonce,
        "device_key_id": key_id,
        "measurement_sha256": measurement_hash,
    }
    for field, expected in expected_fields.items():
        if response.get(field) != expected:
            raise VerificationError(f"RESPONSE_BINDING_MISMATCH:{field}")
    signed_at = _parse_time(response.get("signed_at_utc"), "signed_at_utc")
    if signed_at < issued - timedelta(seconds=30) or signed_at >= expires:
        raise VerificationError("RESPONSE_TIME_OUTSIDE_CHALLENGE")

    _verify_signature(enrolled_device_public_key_pem, response_signature_b64, canonical_json(response))

    return {
        "schema": "brain-phone-base.identity-verification-result.v1",
        "status": "SIGNATURE_VALID_IDENTITY_UNVERIFIED",
        "challenge_signature_valid": True,
        "device_response_signature_valid": True,
        "measurement_binding_valid": True,
        "challenge_replay_check": "caller_supplied" if seen_challenge_ids is not None else "NOT_CONFIGURED",
        "hardware_backed_key_verified": False,
        "android_key_attestation_verified": False,
        "device_identity_verified": False,
        "trusted": False,
        "active": False,
        "manual_approval": "NOT_GRANTED",
        "mining": "DISABLED",
        "network_upload": False,
        "next_requirement": "Validate Android Key Attestation and the enrolled device key before any trust decision.",
    }

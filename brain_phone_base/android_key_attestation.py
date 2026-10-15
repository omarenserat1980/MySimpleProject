#!/usr/bin/env python3
"""Fail-closed Android Key Attestation certificate-chain and challenge checks.

This module intentionally stops short of the complete Android attestation policy:
application identity, verified-boot/device-lock state, patch-level policy, revocation,
and hardware security-level policy still require explicit verifier configuration.
A successful result never grants device trust or activation.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable

ATTESTATION_EXTENSION_OID = "1.3.6.1.4.1.11129.2.1.17"
_SECURITY_LEVELS = {0: "SOFTWARE", 1: "TRUSTED_ENVIRONMENT", 2: "STRONG_BOX"}


class AttestationError(ValueError):
    """A fail-closed Android attestation validation error."""


def _der_value(data: bytes, offset: int = 0) -> tuple[int, bytes, int]:
    """Read one strict DER TLV, returning tag, value, and next offset."""
    if offset + 2 > len(data):
        raise AttestationError("ATTESTATION_DER_TRUNCATED")
    tag = data[offset]
    first_length = data[offset + 1]
    cursor = offset + 2
    if first_length < 0x80:
        length = first_length
    else:
        count = first_length & 0x7F
        if count == 0 or count > 4 or cursor + count > len(data):
            raise AttestationError("ATTESTATION_DER_LENGTH_INVALID")
        if data[cursor] == 0:
            raise AttestationError("ATTESTATION_DER_NON_CANONICAL")
        length = int.from_bytes(data[cursor:cursor + count], "big")
        if length < 0x80:
            raise AttestationError("ATTESTATION_DER_NON_CANONICAL")
        cursor += count
    end = cursor + length
    if end > len(data):
        raise AttestationError("ATTESTATION_DER_TRUNCATED")
    return tag, data[cursor:end], end


def _attestation_fields(extension_der: bytes) -> tuple[bytes, int, int]:
    tag, sequence, end = _der_value(extension_der)
    if tag != 0x30 or end != len(extension_der):
        raise AttestationError("ATTESTATION_DESCRIPTION_INVALID")
    values: list[tuple[int, bytes]] = []
    cursor = 0
    while cursor < len(sequence):
        item_tag, item_value, cursor = _der_value(sequence, cursor)
        values.append((item_tag, item_value))
        if len(values) > 64:
            raise AttestationError("ATTESTATION_DESCRIPTION_TOO_LARGE")
    if len(values) < 6:
        raise AttestationError("ATTESTATION_DESCRIPTION_TRUNCATED")
    if [values[i][0] for i in range(4)] != [0x02, 0x0A, 0x02, 0x0A]:
        raise AttestationError("ATTESTATION_DESCRIPTION_FIELDS_INVALID")
    if values[4][0] != 0x04 or values[5][0] != 0x04:
        raise AttestationError("ATTESTATION_CHALLENGE_FIELD_INVALID")
    attestation_level = int.from_bytes(values[1][1], "big", signed=False)
    keymaster_level = int.from_bytes(values[3][1], "big", signed=False)
    if attestation_level not in _SECURITY_LEVELS or keymaster_level not in _SECURITY_LEVELS:
        raise AttestationError("ATTESTATION_SECURITY_LEVEL_UNKNOWN")
    return values[4][1], attestation_level, keymaster_level


def _verify_cert_signature(cert, issuer) -> None:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, ed25519, ed448, padding, rsa

    key = issuer.public_key()
    try:
        if isinstance(key, rsa.RSAPublicKey):
            algorithm = cert.signature_hash_algorithm
            if isinstance(algorithm, (hashes.SHA1, hashes.MD5)):
                raise AttestationError("CERT_SIGNATURE_HASH_TOO_WEAK")
            if algorithm is None:
                raise AttestationError("CERT_SIGNATURE_ALGORITHM_UNSUPPORTED")
            key.verify(cert.signature, cert.tbs_certificate_bytes, padding.PKCS1v15(), algorithm)
        elif isinstance(key, ec.EllipticCurvePublicKey):
            algorithm = cert.signature_hash_algorithm
            if isinstance(algorithm, (hashes.SHA1, hashes.MD5)):
                raise AttestationError("CERT_SIGNATURE_HASH_TOO_WEAK")
            if algorithm is None:
                raise AttestationError("CERT_SIGNATURE_ALGORITHM_UNSUPPORTED")
            key.verify(cert.signature, cert.tbs_certificate_bytes, ec.ECDSA(algorithm))
        elif isinstance(key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
            key.verify(cert.signature, cert.tbs_certificate_bytes)
        else:
            raise AttestationError("CERT_PUBLIC_KEY_UNSUPPORTED")
    except AttestationError:
        raise
    except Exception as exc:
        raise AttestationError("CERT_SIGNATURE_INVALID") from exc


def _check_time(cert, now: datetime) -> None:
    before = getattr(cert, "not_valid_before_utc", None)
    after = getattr(cert, "not_valid_after_utc", None)
    if before is None:
        before = cert.not_valid_before.replace(tzinfo=timezone.utc)
    if after is None:
        after = cert.not_valid_after.replace(tzinfo=timezone.utc)
    if now < before or now > after:
        raise AttestationError("CERTIFICATE_OUTSIDE_VALIDITY")


def verify_android_key_attestation_chain(
    *,
    certificate_chain: Iterable[bytes],
    trusted_root_sha256_fingerprints: set[str],
    expected_attestation_challenge: bytes,
    expected_device_public_key_pem: bytes,
    now: datetime | None = None,
) -> dict[str, object]:
    """Validate an ordered leaf-to-root chain against out-of-band root pins.

    Certificate bytes may be DER or PEM. Root pins are SHA-256 certificate
    fingerprints as 64 hexadecimal characters, not public-key fingerprints.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        from cryptography.x509.oid import ObjectIdentifier
    except ImportError as exc:
        raise AttestationError("CRYPTO_BACKEND_UNAVAILABLE") from exc

    if not isinstance(expected_attestation_challenge, bytes) or not expected_attestation_challenge:
        raise AttestationError("EXPECTED_CHALLENGE_REQUIRED")
    pins = {pin.replace(":", "").lower() for pin in trusted_root_sha256_fingerprints}
    if not pins or any(len(pin) != 64 or any(ch not in "0123456789abcdef" for ch in pin) for pin in pins):
        raise AttestationError("TRUSTED_ROOT_PINS_INVALID")
    try:
        raw_chain = list(certificate_chain)
    except TypeError as exc:
        raise AttestationError("CERTIFICATE_CHAIN_INVALID") from exc
    if not 2 <= len(raw_chain) <= 10:
        raise AttestationError("CERTIFICATE_CHAIN_LENGTH_INVALID")

    certs = []
    for raw in raw_chain:
        if not isinstance(raw, bytes):
            raise AttestationError("CERTIFICATE_ENCODING_INVALID")
        try:
            cert = x509.load_pem_x509_certificate(raw) if raw.lstrip().startswith(b"-----BEGIN CERTIFICATE-----") else x509.load_der_x509_certificate(raw)
        except (ValueError, TypeError) as exc:
            raise AttestationError("CERTIFICATE_ENCODING_INVALID") from exc
        certs.append(cert)

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    for cert in certs:
        _check_time(cert, current)

    leaf, root = certs[0], certs[-1]
    from cryptography.hazmat.primitives import hashes
    root_fingerprint = root.fingerprint(hashes.SHA256()).hex()
    if root_fingerprint not in pins:
        raise AttestationError("ROOT_CERTIFICATE_NOT_PINNED")
    if root.subject != root.issuer:
        raise AttestationError("ROOT_NOT_SELF_ISSUED")
    _verify_cert_signature(root, root)

    for index, cert in enumerate(certs[:-1]):
        issuer = certs[index + 1]
        if cert.issuer != issuer.subject:
            raise AttestationError("CERTIFICATE_ISSUER_MISMATCH")
        try:
            constraints = issuer.extensions.get_extension_for_class(x509.BasicConstraints).value
        except x509.ExtensionNotFound as exc:
            raise AttestationError("ISSUER_CA_CONSTRAINTS_MISSING") from exc
        if not constraints.ca:
            raise AttestationError("ISSUER_NOT_CA")
        try:
            issuer_usage = issuer.extensions.get_extension_for_class(x509.KeyUsage).value
            if not issuer_usage.key_cert_sign:
                raise AttestationError("ISSUER_CANNOT_SIGN_CERTIFICATES")
        except x509.ExtensionNotFound as exc:
            raise AttestationError("ISSUER_KEY_USAGE_MISSING") from exc
        _verify_cert_signature(cert, issuer)

    try:
        leaf_constraints = leaf.extensions.get_extension_for_class(x509.BasicConstraints).value
        if leaf_constraints.ca:
            raise AttestationError("ATTESTATION_LEAF_MUST_NOT_BE_CA")
    except x509.ExtensionNotFound:
        pass
    try:
        key_usage = leaf.extensions.get_extension_for_class(x509.KeyUsage).value
        if not key_usage.digital_signature:
            raise AttestationError("ATTESTATION_KEY_CANNOT_SIGN")
    except x509.ExtensionNotFound:
        raise AttestationError("ATTESTATION_KEY_USAGE_MISSING")

    try:
        extension = leaf.extensions.get_extension_for_oid(ObjectIdentifier(ATTESTATION_EXTENSION_OID)).value
    except x509.ExtensionNotFound as exc:
        raise AttestationError("ANDROID_KEY_ATTESTATION_EXTENSION_MISSING") from exc
    if not isinstance(extension, x509.UnrecognizedExtension):
        raise AttestationError("ANDROID_KEY_ATTESTATION_EXTENSION_UNEXPECTED_TYPE")
    attestation_challenge, attestation_level, keymaster_level = _attestation_fields(extension.value)
    if attestation_challenge != expected_attestation_challenge:
        raise AttestationError("ATTESTATION_CHALLENGE_MISMATCH")

    try:
        expected_key = serialization.load_pem_public_key(expected_device_public_key_pem)
    except (ValueError, TypeError) as exc:
        raise AttestationError("EXPECTED_DEVICE_KEY_INVALID") from exc
    expected_spki = expected_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    leaf_spki = leaf.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    if not hashlib.sha256(expected_spki).digest() == hashlib.sha256(leaf_spki).digest():
        raise AttestationError("ATTESTATION_LEAF_KEY_MISMATCH")

    return {
        "schema": "brain-phone-base.android-attestation-chain-result.v1",
        "status": "CHAIN_AND_CHALLENGE_VALID_POLICY_INCOMPLETE",
        "certificate_chain_valid": True,
        "root_pin_valid": True,
        "attestation_challenge_matches": True,
        "attested_public_key_matches": True,
        "attestation_security_level_reported": _SECURITY_LEVELS[attestation_level],
        "keymaster_security_level_reported": _SECURITY_LEVELS[keymaster_level],
        "application_identity_policy_checked": False,
        "verified_boot_policy_checked": False,
        "patch_level_policy_checked": False,
        "revocation_checked": False,
        "android_key_attestation_verified": False,
        "device_identity_verified": False,
        "trusted": False,
        "active": False,
        "manual_approval": "NOT_GRANTED",
        "mining": "DISABLED",
        "next_requirement": "Apply reviewed application identity, verified-boot, patch-level, revocation, and hardware security-level policy.",
    }

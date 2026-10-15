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
    first_tag_octet = data[offset]
    cursor = offset + 1
    if (first_tag_octet & 0x1F) == 0x1F:
        tag_number = 0
        first_component = True
        while True:
            if cursor >= len(data):
                raise AttestationError("ATTESTATION_DER_TAG_TRUNCATED")
            octet = data[cursor]
            cursor += 1
            if first_component and (octet & 0x7F) == 0:
                raise AttestationError("ATTESTATION_DER_TAG_NON_CANONICAL")
            first_component = False
            tag_number = (tag_number << 7) | (octet & 0x7F)
            if tag_number > 0xFFFF:
                raise AttestationError("ATTESTATION_DER_TAG_TOO_LARGE")
            if not (octet & 0x80):
                break
        if tag_number < 31:
            raise AttestationError("ATTESTATION_DER_TAG_NON_CANONICAL")
        tag = (first_tag_octet << 16) | tag_number
    else:
        tag = first_tag_octet
    if cursor >= len(data):
        raise AttestationError("ATTESTATION_DER_TRUNCATED")
    first_length = data[cursor]
    cursor += 1
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


def _parse_attestation_description(extension_der: bytes) -> dict[str, object]:
    tag, sequence, end = _der_value(extension_der)
    if tag != 0x30 or end != len(extension_der):
        raise AttestationError("ATTESTATION_DESCRIPTION_INVALID")
    fields = []
    cursor = 0
    while cursor < len(sequence):
        item_tag, item_value, cursor = _der_value(sequence, cursor)
        fields.append((item_tag, item_value))
    if len(fields) != 8:
        raise AttestationError("ATTESTATION_DESCRIPTION_FIELD_COUNT_INVALID")
    if fields[6][0] != 0x30 or fields[7][0] != 0x30:
        raise AttestationError("ATTESTATION_AUTHORIZATION_LIST_INVALID")
    return {
        "attestation_version": int.from_bytes(fields[0][1], "big"),
        "attestation_security_level": int.from_bytes(fields[1][1], "big"),
        "keymaster_version": int.from_bytes(fields[2][1], "big"),
        "keymaster_security_level": int.from_bytes(fields[3][1], "big"),
        "challenge": fields[4][1],
        "unique_id": fields[5][1],
        "software_enforced": _parse_authorization_list(fields[6][1]),
        "tee_enforced": _parse_authorization_list(fields[7][1]),
    }


def _parse_authorization_list(sequence: bytes) -> dict[int, tuple[int, bytes]]:
    values: dict[int, tuple[int, bytes]] = {}
    cursor = 0
    while cursor < len(sequence):
        tag, encoded, cursor = _der_value(sequence, cursor)
        if (tag >> 16) == 0xBF:
            number = tag & 0xFFFF
        elif tag <= 0xFF and (tag & 0xE0) == 0xA0:
            number = tag & 0x1F
        else:
            raise AttestationError("AUTHORIZATION_TAG_INVALID")
        if number in values:
            raise AttestationError("AUTHORIZATION_TAG_DUPLICATE")
        inner_tag, inner_value, inner_end = _der_value(encoded)
        if inner_end != len(encoded):
            raise AttestationError("AUTHORIZATION_VALUE_INVALID")
        values[number] = (inner_tag, inner_value)
    return values


def _integer_authorization(auth: dict[int, tuple[int, bytes]], number: int) -> int | None:
    item = auth.get(number)
    if item is None:
        return None
    tag, value = item
    if tag != 0x02 or not value:
        raise AttestationError("AUTHORIZATION_INTEGER_INVALID")
    return int.from_bytes(value, "big", signed=False)


def _patch_level(tee: dict[int, tuple[int, bytes]], software: dict[int, tuple[int, bytes]], number: int) -> int | None:
    tee_value = _integer_authorization(tee, number)
    software_value = _integer_authorization(software, number)
    if tee_value is not None and software_value is not None and tee_value != software_value:
        raise AttestationError("PATCH_LEVEL_CONFLICT")
    return tee_value if tee_value is not None else software_value


def _verify_boot_state(tee: dict[int, tuple[int, bytes]], require_device_locked: bool, require_verified_boot_green: bool) -> dict[str, object]:
    item = tee.get(704)  # RootOfTrust is context-specific tag [704].
    if item is None:
        if require_device_locked or require_verified_boot_green:
            raise AttestationError("ROOT_OF_TRUST_MISSING")
        return {"device_locked": None, "verified_boot_state": None}
    tag, value = item
    if tag != 0x30:
        raise AttestationError("ROOT_OF_TRUST_INVALID")
    fields = []
    cursor = 0
    while cursor < len(value):
        ftag, fvalue, cursor = _der_value(value, cursor)
        fields.append((ftag, fvalue))
    if len(fields) < 3 or fields[0][0] != 0x04 or fields[1][0] != 0x01 or fields[2][0] != 0x0A:
        raise AttestationError("ROOT_OF_TRUST_FIELDS_INVALID")
    if fields[1][1] not in (b"\x00", b"\xff"):
        raise AttestationError("DEVICE_LOCKED_VALUE_INVALID")
    device_locked = fields[1][1] == b"\xff"
    verified_state = int.from_bytes(fields[2][1], "big")
    if require_device_locked and not device_locked:
        raise AttestationError("DEVICE_NOT_LOCKED")
    if require_verified_boot_green and verified_state != 0:
        raise AttestationError("VERIFIED_BOOT_NOT_GREEN")
    return {"device_locked": device_locked, "verified_boot_state": {0: "VERIFIED", 1: "SELF_SIGNED", 2: "UNVERIFIED", 3: "FAILED"}.get(verified_state, "UNKNOWN")}


def _verify_application_identity(tee: dict[str, tuple[int, bytes]], software: dict[str, tuple[int, bytes]], expected_package: str | None, expected_signers: set[str] | None) -> dict[str, object]:
    # AttestationApplicationId (tag [709]) is DER-encoded in the extension.
    item = tee.get(709) or software.get(709)
    if expected_package is None and expected_signers is None:
        return {"checked": False, "reason": "EXPECTED_APPLICATION_IDENTITY_NOT_CONFIGURED"}
    if not expected_package or not expected_signers:
        raise AttestationError("APPLICATION_IDENTITY_POLICY_INCOMPLETE")
    if item is None:
        raise AttestationError("ATTESTATION_APPLICATION_ID_MISSING")
    tag, value = item
    if tag != 0x04:
        raise AttestationError("ATTESTATION_APPLICATION_ID_INVALID")
    app_tag, app_seq, app_end = _der_value(value)
    if app_tag != 0x30 or app_end != len(value):
        raise AttestationError("ATTESTATION_APPLICATION_ID_INVALID")
    fields = []
    cursor = 0
    while cursor < len(app_seq):
        ftag, fvalue, cursor = _der_value(app_seq, cursor)
        fields.append((ftag, fvalue))
    if len(fields) != 2 or fields[0][0] != 0x31 or fields[1][0] != 0x31:
        raise AttestationError("ATTESTATION_APPLICATION_ID_FIELDS_INVALID")
    package_names = set()
    cursor = 0
    while cursor < len(fields[0][1]):
        st, sv, cursor = _der_value(fields[0][1], cursor)
        if st != 0x30:
            raise AttestationError("ATTESTATION_PACKAGE_INFO_INVALID")
        part = 0
        inner = []
        while part < len(sv):
            it, iv, part = _der_value(sv, part)
            inner.append((it, iv))
        if len(inner) != 2 or inner[0][0] != 0x0C:
            raise AttestationError("ATTESTATION_PACKAGE_INFO_INVALID")
        package_names.add(inner[0][1].decode("utf-8", errors="strict"))
    signer_hashes = set()
    cursor = 0
    while cursor < len(fields[1][1]):
        st, sv, cursor = _der_value(fields[1][1], cursor)
        if st != 0x04:
            raise AttestationError("ATTESTATION_SIGNER_DIGEST_INVALID")
        signer_hashes.add(sv.hex())
    expected = {value.replace(":", "").lower() for value in expected_signers}
    if expected_package not in package_names or not (expected & signer_hashes):
        raise AttestationError("ATTESTATION_APPLICATION_ID_MISMATCH")
    return {"checked": True, "package_name_match": True, "signing_certificate_digest_match": True}


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
    expected_application_package_name: str | None = None,
    expected_application_signing_cert_sha256: set[str] | None = None,
    minimum_os_patch_level: int | None = None,
    minimum_vendor_patch_level: int | None = None,
    minimum_boot_patch_level: int | None = None,
    minimum_key_security_level: str = "TRUSTED_ENVIRONMENT",
    require_device_locked: bool = True,
    require_verified_boot_green: bool = True,
    require_hardware_enforced_authorization: bool = True,
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
    # Parse the complete ASN.1 AuthorizationList only after chain validation.
    # Android's schema uses context-specific explicit tags; unknown or malformed
    # structures are rejected rather than interpreted permissively.
    description = _parse_attestation_description(extension.value)
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

    if minimum_key_security_level not in {"SOFTWARE", "TRUSTED_ENVIRONMENT", "STRONG_BOX"}:
        raise AttestationError("MINIMUM_SECURITY_LEVEL_INVALID")
    level_rank = {"SOFTWARE": 0, "TRUSTED_ENVIRONMENT": 1, "STRONG_BOX": 2}
    if level_rank[_SECURITY_LEVELS[attestation_level]] < level_rank[minimum_key_security_level] or level_rank[_SECURITY_LEVELS[keymaster_level]] < level_rank[minimum_key_security_level]:
        raise AttestationError("HARDWARE_SECURITY_LEVEL_BELOW_POLICY")

    tee = description["tee_enforced"]
    software = description["software_enforced"]
    if require_hardware_enforced_authorization and not tee:
        raise AttestationError("TEE_AUTHORIZATION_LIST_EMPTY")
    os_patch = _patch_level(tee, software, 706)
    vendor_patch = _patch_level(tee, software, 718)
    boot_patch = _patch_level(tee, software, 719)
    if minimum_os_patch_level is not None and (os_patch is None or os_patch < minimum_os_patch_level):
        raise AttestationError("OS_PATCH_LEVEL_BELOW_POLICY")
    if minimum_vendor_patch_level is not None and (vendor_patch is None or vendor_patch < minimum_vendor_patch_level):
        raise AttestationError("VENDOR_PATCH_LEVEL_BELOW_POLICY")
    if minimum_boot_patch_level is not None and (boot_patch is None or boot_patch < minimum_boot_patch_level):
        raise AttestationError("BOOT_PATCH_LEVEL_BELOW_POLICY")

    boot_state = _verify_boot_state(tee, require_device_locked, require_verified_boot_green)
    application_identity = _verify_application_identity(
        tee, software, expected_application_package_name, expected_application_signing_cert_sha256
    )

    return {
        "schema": "brain-phone-base.android-attestation-chain-result.v1",
        "status": "CHAIN_AND_CHALLENGE_VALID_POLICY_INCOMPLETE",
        "certificate_chain_valid": True,
        "root_pin_valid": True,
        "attestation_challenge_matches": True,
        "attested_public_key_matches": True,
        "attestation_security_level_reported": _SECURITY_LEVELS[attestation_level],
        "keymaster_security_level_reported": _SECURITY_LEVELS[keymaster_level],
        "application_identity_policy_checked": expected_application_package_name is not None and expected_application_signing_cert_sha256 is not None,
        "application_identity": application_identity,
        "verified_boot_policy_checked": True,
        "verified_boot": boot_state,
        "patch_level_policy_checked": any(v is not None for v in (minimum_os_patch_level, minimum_vendor_patch_level, minimum_boot_patch_level)),
        "patch_levels": {"os": os_patch, "vendor": vendor_patch, "boot": boot_patch},
        "hardware_security_level_policy_checked": True,
        "revocation_checked": False,
        "android_key_attestation_verified": False,
        "device_identity_verified": False,
        "trusted": False,
        "active": False,
        "manual_approval": "NOT_GRANTED",
        "mining": "DISABLED",
        "next_requirement": "Apply reviewed application identity, verified-boot, patch-level, revocation, and hardware security-level policy.",
    }

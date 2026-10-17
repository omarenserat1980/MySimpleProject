"""Bitcoin header assembly and local share-target validation.

This module is deliberately offline-only. It never opens a pool connection,
loads credentials, submits a share, or claims pool acceptance. Callers must
convert Stratum wire fields to Bitcoin's serialized byte order explicitly
before assembling the header; the API uses names that make that boundary clear.
"""
from __future__ import annotations

import hashlib
from typing import Any


def _decode_hex(value: Any, field: str, expected_bytes: int) -> bytes:
    if not isinstance(value, str) or len(value) != expected_bytes * 2:
        raise ValueError("INVALID_" + field.upper() + "_HEX_LENGTH")
    try:
        decoded = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("INVALID_" + field.upper() + "_HEX") from exc
    if len(decoded) != expected_bytes:
        raise ValueError("INVALID_" + field.upper() + "_BYTE_LENGTH")
    return decoded


def sha256d(data: bytes) -> bytes:
    """Return the raw 32-byte SHA256d digest."""
    if not isinstance(data, bytes):
        raise ValueError("DATA_MUST_BE_BYTES")
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def validate_target(target: int, field: str = "target") -> None:
    if isinstance(target, bool) or not isinstance(target, int) or not 0 < target < 2**256:
        raise ValueError("INVALID_" + field.upper())


def assemble_header(
    *,
    version_le_hex: str,
    prevhash_le_hex: str,
    merkle_root_le_hex: str,
    ntime_le_hex: str,
    nbits_le_hex: str,
    nonce: int,
) -> bytes:
    """Assemble an 80-byte header from fields already in serialized byte order.

    The caller is responsible for Stratum-specific prevhash/merkle byte-order
    conversion. This function intentionally does not guess or silently reverse
    protocol fields. Nonce is encoded as uint32 little-endian.
    """
    if isinstance(nonce, bool) or not isinstance(nonce, int) or not 0 <= nonce <= 0xFFFFFFFF:
        raise ValueError("NONCE_OUT_OF_RANGE")
    fields = (
        _decode_hex(version_le_hex, "version_le", 4),
        _decode_hex(prevhash_le_hex, "prevhash_le", 32),
        _decode_hex(merkle_root_le_hex, "merkle_root_le", 32),
        _decode_hex(ntime_le_hex, "ntime_le", 4),
        _decode_hex(nbits_le_hex, "nbits_le", 4),
        nonce.to_bytes(4, "little"),
    )
    header = b"".join(fields)
    if len(header) != 80:
        raise AssertionError("BITCOIN_HEADER_LENGTH_INVARIANT_FAILED")
    return header


def validate_share_candidate(
    header: bytes,
    *,
    nonce: int,
    share_target: int,
    network_target: int | None = None,
) -> dict[str, Any]:
    """Check a candidate against a pool share target and optional network target.

    A positive result means only that the local hash meets the supplied target.
    It does not prove the pool received or accepted the share.
    """
    if not isinstance(header, bytes) or len(header) != 80:
        raise ValueError("BITCOIN_HEADER_MUST_BE_80_BYTES")
    if isinstance(nonce, bool) or not isinstance(nonce, int) or not 0 <= nonce <= 0xFFFFFFFF:
        raise ValueError("NONCE_OUT_OF_RANGE")
    encoded_nonce = nonce.to_bytes(4, "little")
    if header[76:80] != encoded_nonce:
        raise ValueError("HEADER_NONCE_MISMATCH")
    validate_target(share_target, "share_target")
    if network_target is not None:
        validate_target(network_target, "network_target")

    digest = sha256d(header)
    digest_value = int.from_bytes(digest, "little")
    meets_share_target = digest_value <= share_target
    meets_network_target = (
        digest_value <= network_target if network_target is not None else None
    )
    return {
        "schema_version": 1,
        "status": "LOCAL_SHARE_TARGET_MET" if meets_share_target else "SHARE_TARGET_NOT_MET",
        "header_sha256d_display_hex": digest[::-1].hex(),
        "nonce": nonce,
        "hashes_checked": 1,
        "share_target_met": meets_share_target,
        "network_target_met": meets_network_target,
        "pool_submission_attempted": False,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
        "revenue_verified": False,
        "evidence_class": "LOCAL_CRYPTOGRAPHIC_CANDIDATE_ONLY",
    }

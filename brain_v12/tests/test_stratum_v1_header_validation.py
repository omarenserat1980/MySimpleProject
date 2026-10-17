"""Offline tests for the explicit-byte-order Bitcoin header validator."""
import hashlib

import pytest

from brain_v12.brain.stratum_v1_header_validation import (
    assemble_header,
    sha256d,
    validate_share_candidate,
)


def header(nonce=7):
    return assemble_header(
        version_le_hex="01000000",
        prevhash_le_hex="00" * 32,
        merkle_root_le_hex="11" * 32,
        ntime_le_hex="aabbccdd",
        nbits_le_hex="ffff001d",
        nonce=nonce,
    )


def test_header_assembly_is_exactly_80_bytes_and_nonce_is_little_endian():
    value = header(0x12345678)
    assert len(value) == 80
    assert value[:4] == bytes.fromhex("01000000")
    assert value[72:76] == bytes.fromhex("ffff001d")
    assert value[76:80] == bytes.fromhex("78563412")


def test_sha256d_matches_independent_standard_library_calculation():
    payload = b"Electronic Brain offline test"
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
    assert sha256d(payload) == expected


def test_maximum_target_accepts_local_hash_but_never_claims_pool_acceptance():
    value = header(7)
    result = validate_share_candidate(
        value, nonce=7, share_target=(1 << 256) - 1, network_target=1
    )
    assert result["status"] == "LOCAL_SHARE_TARGET_MET"
    assert result["share_target_met"] is True
    assert result["network_target_met"] is False
    assert result["pool_submission_attempted"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_impossible_target_does_not_claim_share_candidate():
    result = validate_share_candidate(header(), nonce=7, share_target=1)
    assert result["status"] == "SHARE_TARGET_NOT_MET"
    assert result["share_target_met"] is False
    assert result["pool_acceptance_verified"] is False


def test_rejects_header_nonce_mismatch():
    with pytest.raises(ValueError, match="HEADER_NONCE_MISMATCH"):
        validate_share_candidate(header(8), nonce=7, share_target=(1 << 256) - 1)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"version_le_hex": "00", "prevhash_le_hex": "00" * 32,
          "merkle_root_le_hex": "00" * 32, "ntime_le_hex": "00" * 4,
          "nbits_le_hex": "00" * 4, "nonce": 0}, "INVALID_VERSION_LE_HEX_LENGTH"),
        ({"version_le_hex": "zz" * 4, "prevhash_le_hex": "00" * 32,
          "merkle_root_le_hex": "00" * 32, "ntime_le_hex": "00" * 4,
          "nbits_le_hex": "00" * 4, "nonce": 0}, "INVALID_VERSION_LE_HEX"),
        ({"version_le_hex": "00" * 4, "prevhash_le_hex": "00" * 32,
          "merkle_root_le_hex": "00" * 32, "ntime_le_hex": "00" * 4,
          "nbits_le_hex": "00" * 4, "nonce": True}, "NONCE_OUT_OF_RANGE"),
    ],
)
def test_header_assembly_rejects_malformed_fields(kwargs, message):
    with pytest.raises(ValueError, match=message):
        assemble_header(**kwargs)


@pytest.mark.parametrize("target", [0, -1, 1 << 256, True, 1.5])
def test_share_target_must_be_valid_256_bit_positive_integer(target):
    with pytest.raises(ValueError, match="INVALID_SHARE_TARGET"):
        validate_share_candidate(header(), nonce=7, share_target=target)

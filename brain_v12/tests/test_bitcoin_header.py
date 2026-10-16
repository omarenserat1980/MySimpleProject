import pytest

from brain_v12.brain.bitcoin_header import (
    build_header_candidate,
    compact_nbits_to_target,
    verify_candidate_against_target,
)


def test_header_is_exactly_80_bytes_and_nonce_little_endian():
    candidate = build_header_candidate(
        version_hex="01000000",
        prevhash_wire_hex="00" * 32,
        merkle_root_raw=b"\x11" * 32,
        ntime_hex="02000000",
        nbits_hex="ffff001d",
        nonce=0x12345678,
        share_target=2**256 - 1,
    )
    assert len(candidate.header_bytes) == 80
    assert candidate.header_bytes[-4:] == bytes.fromhex("78563412")
    assert candidate.meets_share_target is True


def test_invalid_header_fields_are_rejected():
    with pytest.raises(ValueError, match="INVALID_VERSION_WIDTH"):
        build_header_candidate(
            version_hex="01", prevhash_wire_hex="00" * 32,
            merkle_root_raw=b"\x11" * 32, ntime_hex="02000000",
            nbits_hex="ffff001d", nonce=0, share_target=1,
        )


def test_compact_target_decoding():
    # Bitcoin mainnet's canonical nBits bytes for 0x1d00ffff are ff ff 00 1d.
    target = compact_nbits_to_target("ffff001d")
    assert target == 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def test_compact_target_rejects_negative_and_zero():
    with pytest.raises(ValueError, match="INVALID_COMPACT_TARGET"):
        compact_nbits_to_target("ffff009d")
    with pytest.raises(ValueError, match="INVALID_COMPACT_TARGET"):
        compact_nbits_to_target("00000000")


def test_hash_verification_never_claims_pool_acceptance():
    result = verify_candidate_against_target(b"\x00" * 80, 2**256 - 1)
    assert result["hash_integer_meets_target"] is True
    assert result["pool_share_acceptance_verified"] is False


def test_bitcoin_genesis_header_sha256d_known_vector():
    candidate = build_header_candidate(
        version_hex="01000000",
        prevhash_wire_hex="00" * 32,
        merkle_root_raw=bytes.fromhex(
            "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
        ),
        ntime_hex="29ab5f49",
        nbits_hex="ffff001d",
        nonce=0x7C2BAC1D,
        share_target=compact_nbits_to_target("ffff001d"),
    )
    assert candidate.digest_display_hex == (
        "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
    )
    assert candidate.meets_share_target is True

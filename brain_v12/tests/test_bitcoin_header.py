import pytest

from brain_v12.brain.bitcoin_header import (
    build_header_candidate,
    compact_nbits_to_target,
    verify_candidate_against_target,
    stratum_v1_prevhash_to_header_wire_hex,
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


def test_legacy_stratum_v1_prevhash_known_word_endian_vector():
    # Observed legacy Stratum mining.notify example for block 672486; the pool
    # hash is encoded as eight little-endian 32-bit words. See the cited source
    # in docs/BRAIN_STRATUM_V1_PREVHASH_BYTE_ORDER.md.
    stratum_prevhash = (
        "852ab3acf6baeb51e883cc88f49ef03a"
        "e17ed8110009a5fb0000000000000000"
    )
    assert stratum_v1_prevhash_to_header_wire_hex(stratum_prevhash) == (
        "acb32a8551ebbaf688cc83e83af09ef4"
        "11d87ee1fba509000000000000000000"
    )


def test_stratum_prevhash_normalizer_rejects_invalid_width():
    with pytest.raises(ValueError, match="INVALID_STRATUM_V1_PREVHASH_WIDTH"):
        stratum_v1_prevhash_to_header_wire_hex("00" * 31)



def test_fixed_width_header_fields_reject_embedded_whitespace():
    with pytest.raises(ValueError, match="INVALID_VERSION_HEX"):
        build_header_candidate(
            version_hex="01 00000",
            prevhash_wire_hex="00" * 32,
            merkle_root_raw=b"\x11" * 32,
            ntime_hex="02000000",
            nbits_hex="ffff001d",
            nonce=0,
            share_target=2**256 - 1,
        )


def test_genesis_hash_integer_matches_independent_display_vector():
    expected_display = (
        "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
    )
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
    assert candidate.digest_display_hex == expected_display
    assert candidate.hash_integer == int(expected_display, 16)
    assert candidate.hash_integer <= compact_nbits_to_target("ffff001d")


def test_target_comparison_is_inclusive_at_exact_boundary():
    header = bytes.fromhex("00" * 80)
    exact = verify_candidate_against_target(header, 2**256 - 1)
    assert exact["hash_integer_meets_target"] is True
    below_hash = exact["hash_integer"] - 1
    if below_hash > 0:
        rejected = verify_candidate_against_target(header, below_hash)
        assert rejected["hash_integer_meets_target"] is False



@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("version_hex", "0100000g", "INVALID_VERSION_HEX"),
        ("ntime_hex", "020 0000", "INVALID_NTIME_HEX"),
        ("nbits_hex", "ffff00zz", "INVALID_NBITS_HEX"),
        ("prevhash_wire_hex", "00" * 15 + "  " + "00" * 16, "INVALID_PREVHASH_WIRE_HEX"),
    ],
)
def test_header_fields_reject_non_hex_and_embedded_whitespace(field, value, expected):
    args = {
        "version_hex": "01000000",
        "prevhash_wire_hex": "00" * 32,
        "merkle_root_raw": b"\x11" * 32,
        "ntime_hex": "02000000",
        "nbits_hex": "ffff001d",
        "nonce": 0,
        "share_target": 2**256 - 1,
    }
    args[field] = value
    with pytest.raises(ValueError, match=expected):
        build_header_candidate(**args)


@pytest.mark.parametrize(
    ("nonce", "share_target", "expected"),
    [
        (True, 1, "NONCE_OUT_OF_RANGE"),
        (-1, 1, "NONCE_OUT_OF_RANGE"),
        (0x100000000, 1, "NONCE_OUT_OF_RANGE"),
        (0, True, "SHARE_TARGET_OUT_OF_RANGE"),
        (0, 0, "SHARE_TARGET_OUT_OF_RANGE"),
        (0, 2**256, "SHARE_TARGET_OUT_OF_RANGE"),
    ],
)
def test_header_candidate_rejects_invalid_numeric_boundaries(nonce, share_target, expected):
    with pytest.raises(ValueError, match=expected):
        build_header_candidate(
            version_hex="01000000",
            prevhash_wire_hex="00" * 32,
            merkle_root_raw=b"\x11" * 32,
            ntime_hex="02000000",
            nbits_hex="ffff001d",
            nonce=nonce,
            share_target=share_target,
        )


@pytest.mark.parametrize("merkle_root", [b"", b"\x00" * 31, bytearray(b"\x00" * 32)])
def test_header_candidate_rejects_invalid_merkle_root_type_or_width(merkle_root):
    with pytest.raises(ValueError, match="INVALID_MERKLE_ROOT"):
        build_header_candidate(
            version_hex="01000000",
            prevhash_wire_hex="00" * 32,
            merkle_root_raw=merkle_root,
            ntime_hex="02000000",
            nbits_hex="ffff001d",
            nonce=0,
            share_target=2**256 - 1,
        )


def test_independent_hash_verifier_matches_genesis_header_candidate():
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
    verified = verify_candidate_against_target(candidate.header_bytes, candidate.hash_integer)
    assert verified["header_sha256d_display_hex"] == candidate.digest_display_hex
    assert verified["hash_integer"] == candidate.hash_integer
    assert verified["hash_integer_meets_target"] is True
    just_below = verify_candidate_against_target(candidate.header_bytes, candidate.hash_integer - 1)
    assert just_below["hash_integer_meets_target"] is False
    assert just_below["pool_share_acceptance_verified"] is False


@pytest.mark.parametrize("target", [True, False, 0, -1, 2**256])
def test_independent_hash_verifier_rejects_invalid_target(target):
    with pytest.raises(ValueError, match="TARGET_OUT_OF_RANGE"):
        verify_candidate_against_target(b"\x00" * 80, target)


@pytest.mark.parametrize(
    ("compact", "expected"),
    [
        (0x01010000, 1),       # exponent 1, mantissa 0x010000
        (0x02000100, 1),       # exponent 2, mantissa 0x000100
        (0x02012300, 0x0123),  # exponent 2, right shift by one byte
    ],
)
def test_compact_target_accepts_small_exponents_when_result_is_nonzero(compact, expected):
    encoded = compact.to_bytes(4, "little").hex()
    assert compact_nbits_to_target(encoded) == expected


def test_compact_target_rejects_small_exponent_that_decodes_to_zero():
    # exponent 1 with mantissa 1 shifts right by 16 bits, producing zero.
    with pytest.raises(ValueError, match="COMPACT_TARGET_OUT_OF_RANGE"):
        compact_nbits_to_target((0x01000001).to_bytes(4, "little").hex())

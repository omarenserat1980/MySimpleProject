"""Cross-check Brain SHA-256d implementations at the shared algorithm boundary."""
import hashlib

from brain_v12.asic.bitcoin_pow_simulator import (
    decode_compact_target,
    sha256d as simulator_sha256d,
    simulate_pow,
)
from brain_v12.brain.bitcoin_header import sha256d as header_sha256d
from brain_v12.brain.bitcoin_pow_reference import sha256d as reference_sha256d
from brain_v12.brain.brain_owned_compute_runtime import double_sha256, search_nonce


def test_sha256d_implementations_agree_on_boundary_vectors():
    vectors = (
        b"",
        b"Electronic Brain V12",
        bytes(range(256)),
        bytes(80),
    )
    for payload in vectors:
        expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
        assert simulator_sha256d(payload) == expected
        assert header_sha256d(payload) == expected
        assert reference_sha256d(payload) == expected
        assert double_sha256(payload) == expected


def test_genesis_header_hash_agrees_across_simulator_and_runtime():
    header = bytes.fromhex(
        "01000000"
        + "00" * 32
        + "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
        + "29ab5f49"
        + "ffff001d"
        + "1dac2b7c"
    )
    expected_display_hash = (
        "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
    )
    digest = reference_sha256d(header)
    assert digest[::-1].hex() == expected_display_hash
    assert simulator_sha256d(header)[::-1].hex() == expected_display_hash
    assert double_sha256(header)[::-1].hex() == expected_display_hash
    result = search_nonce(header, int.from_bytes(digest, "little"), start_nonce=2083236893, max_hashes=1)
    assert result.found is True
    assert result.nonce == 2083236893
    assert result.hash_hex == expected_display_hash
    assert result.status == "NONCE_FOUND_UNSUBMITTED"
    # The standalone ASIC simulator and Brain-owned software runtime must agree
    # on the same canonical Bitcoin network target and nonce result.
    network_target = decode_compact_target(0x1D00FFFF)
    simulator_result = simulate_pow(
        header, network_target, start_nonce=2083236893, max_attempts=1
    )
    assert simulator_result.found is True
    assert simulator_result.nonce == result.nonce
    assert simulator_result.hash_hex == result.hash_hex
    assert simulator_result.hash_value <= simulator_result.target

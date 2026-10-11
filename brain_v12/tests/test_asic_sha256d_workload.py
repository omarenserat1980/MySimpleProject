import hashlib

import pytest

from brain_v12.brain.asic_sha256d_workload import search_nonce, sha256d


def test_sha256d_matches_double_sha256():
    payload = b"brain ASIC test"
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()
    assert sha256d(payload) == expected


def test_easy_target_finds_first_nonce_and_labels_software_model():
    prefix = bytes(76)
    result = search_nonce(prefix, 7, 3, 2**256 - 1)
    assert result["found"] is True
    assert result["solution_nonce"] == 7
    assert result["hashes_attempted"] == 1
    assert result["model"] == "SHA256D_SOFTWARE_REFERENCE"
    assert result["hardware_measurement"] is False
    assert result["hashrate_is_asic_estimate"] is False


def test_zero_target_is_bounded_and_does_not_claim_solution():
    result = search_nonce(bytes(76), 0, 2, 0)
    assert result["found"] is False
    assert result["solution_nonce"] is None
    assert result["hashes_attempted"] == 2


@pytest.mark.parametrize(
    "prefix,start,count,target,match",
    [
        (b"x", 0, 1, 0, "HEADER_PREFIX_MUST_BE_76_BYTES"),
        (bytes(76), -1, 1, 0, "NONCE_START_OUT_OF_RANGE"),
        (bytes(76), 0, 0, 0, "NONCE_COUNT_OUT_OF_RANGE"),
        (bytes(76), 0, 1, -1, "TARGET_OUT_OF_RANGE"),
    ],
)
def test_invalid_workload_rejected(prefix, start, count, target, match):
    with pytest.raises(ValueError, match=match):
        search_nonce(prefix, start, count, target)

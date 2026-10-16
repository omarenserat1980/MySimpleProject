"""Tests for disjoint nonce scheduling and explicit checkpoint-style resume."""
import pytest

from brain_v12.brain.brain_owned_compute_runtime import partition_nonce_range, search_nonce


def test_partitions_cover_interval_exactly_without_gaps_or_overlap():
    ranges = partition_nonce_range(10, 31, 6)
    assert ranges == ((10, 14), (14, 18), (18, 22), (22, 25), (25, 28), (28, 31))
    assert ranges[0][0] == 10
    assert ranges[-1][1] == 31
    assert all(start < end for start, end in ranges)
    assert all(ranges[i][1] == ranges[i + 1][0] for i in range(len(ranges) - 1))
    assert sum(end - start for start, end in ranges) == 21


def test_partition_count_larger_than_range_omits_empty_ranges():
    assert partition_nonce_range(7, 9, 20) == ((7, 8), (8, 9))


def test_partition_handles_uint32_max_nonce_with_exclusive_upper_bound():
    assert partition_nonce_range(0xFFFFFFFE, 2**32, 4) == (
        (0xFFFFFFFE, 0xFFFFFFFF), (0xFFFFFFFF, 2**32)
    )


def test_search_resume_starts_after_exactly_checked_nonces_without_overlap():
    # Impossible target ensures the first bounded chunk is exhausted.
    header = bytes(80)
    first = search_nonce(header, 1, start_nonce=100, max_hashes=3)
    assert first.found is False
    assert first.hashes_checked == 3
    checkpoint_next_nonce = 100 + first.hashes_checked
    assert checkpoint_next_nonce == 103

    second = search_nonce(header, 1, start_nonce=checkpoint_next_nonce, max_hashes=2)
    assert second.found is False
    assert second.hashes_checked == 2
    # Ranges [100, 103) and [103, 105) are contiguous and disjoint.
    assert (100, checkpoint_next_nonce) == (100, 103)
    assert (checkpoint_next_nonce, checkpoint_next_nonce + second.hashes_checked) == (103, 105)


def test_invalid_nonce_partitions_fail_closed():
    for args, error in [
        ((-1, 3, 1), "START_NONCE_OUT_OF_RANGE"),
        ((3, 3, 1), "END_NONCE_EXCLUSIVE_OUT_OF_RANGE"),
        ((3, 2, 1), "END_NONCE_EXCLUSIVE_OUT_OF_RANGE"),
        ((3, 2**32 + 1, 1), "END_NONCE_EXCLUSIVE_OUT_OF_RANGE"),
        ((3, 5, 0), "PARTITION_COUNT_OUT_OF_RANGE"),
        ((3, 5, True), "PARTITION_COUNT_OUT_OF_RANGE"),
    ]:
        with pytest.raises(ValueError, match=error):
            partition_nonce_range(*args)

from brain_v12.brain.brain_owned_compute_runtime import (
    build_nonce_search_checkpoint,
    validate_nonce_search_checkpoint,
    sign_nonce_search_checkpoint,
    validate_authenticated_nonce_search_checkpoint,
)


def test_checkpoint_binds_job_header_target_and_next_nonce():
    header = bytes(80)
    target = 1
    result = search_nonce(header, target, start_nonce=200, max_hashes=3)
    checkpoint = build_nonce_search_checkpoint(header, target, "job-A", 200, result)
    assert checkpoint["next_nonce"] == 203
    assert checkpoint["authenticated"] is False
    assert validate_nonce_search_checkpoint(checkpoint, header, target, "job-A") == 203


def test_checkpoint_rejects_changed_job_header_or_target():
    header = bytes(80)
    result = search_nonce(header, 1, start_nonce=10, max_hashes=2)
    checkpoint = build_nonce_search_checkpoint(header, 1, "job-A", 10, result)
    with pytest.raises(ValueError, match="CHECKPOINT_JOB_MISMATCH"):
        validate_nonce_search_checkpoint(checkpoint, header, 1, "job-B")
    with pytest.raises(ValueError, match="CHECKPOINT_HEADER_MISMATCH"):
        validate_nonce_search_checkpoint(checkpoint, bytes([1]) + bytes(79), 1, "job-A")
    with pytest.raises(ValueError, match="CHECKPOINT_TARGET_MISMATCH"):
        validate_nonce_search_checkpoint(checkpoint, header, 2, "job-A")


def test_checkpoint_rejects_found_candidate_and_nonce_space_overflow():
    header = bytes(80)
    found = search_nonce(header, (1 << 256) - 1, start_nonce=0, max_hashes=1)
    with pytest.raises(ValueError, match="CHECKPOINT_REQUIRES_EXHAUSTED_NO_HIT_RESULT"):
        build_nonce_search_checkpoint(header, (1 << 256) - 1, "job-A", 0, found)
    last_chunk = search_nonce(header, 1, start_nonce=0xFFFFFFFF, max_hashes=2)
    with pytest.raises(ValueError, match="NONCE_SPACE_EXHAUSTED"):
        build_nonce_search_checkpoint(header, 1, "job-A", 0xFFFFFFFF, last_chunk)


def test_checkpoint_mutation_fails_closed():
    header = bytes(80)
    result = search_nonce(header, 1, start_nonce=50, max_hashes=1)
    checkpoint = build_nonce_search_checkpoint(header, 1, "job-A", 50, result)
    checkpoint["next_nonce"] = True
    with pytest.raises(ValueError, match="INVALID_CHECKPOINT_NEXT_NONCE"):
        validate_nonce_search_checkpoint(checkpoint, header, 1, "job-A")
    checkpoint["next_nonce"] = 999
    with pytest.raises(ValueError, match="CHECKPOINT_RANGE_ARITHMETIC_MISMATCH"):
        validate_nonce_search_checkpoint(checkpoint, header, 1, "job-A")


_AUTH_TEST_KEY = b"test-only-checkpoint-key-material-32-bytes-minimum"


def _unsigned_checkpoint_for_auth():
    header = bytes(80)
    target = 1
    result = search_nonce(header, target, start_nonce=300, max_hashes=3)
    return header, target, build_nonce_search_checkpoint(header, target, "job-auth", 300, result)


def test_authenticated_checkpoint_round_trip_with_caller_supplied_key():
    header, target, unsigned = _unsigned_checkpoint_for_auth()
    signed = sign_nonce_search_checkpoint(unsigned, header, target, "job-auth", _AUTH_TEST_KEY)
    assert signed["authenticated"] is True
    assert signed["auth_scheme"] == "HMAC-SHA256"
    assert validate_authenticated_nonce_search_checkpoint(signed, header, target, "job-auth", _AUTH_TEST_KEY) == 303


def test_authenticated_checkpoint_rejects_mutation_and_wrong_key():
    header, target, unsigned = _unsigned_checkpoint_for_auth()
    signed = sign_nonce_search_checkpoint(unsigned, header, target, "job-auth", _AUTH_TEST_KEY)
    changed = dict(signed, next_nonce=304)
    with pytest.raises(ValueError, match="CHECKPOINT_AUTHENTICATION_FAILED"):
        validate_authenticated_nonce_search_checkpoint(changed, header, target, "job-auth", _AUTH_TEST_KEY)
    with pytest.raises(ValueError, match="CHECKPOINT_AUTHENTICATION_FAILED"):
        validate_authenticated_nonce_search_checkpoint(signed, header, target, "job-auth", b"x" * 32)


def test_authenticated_checkpoint_requires_strong_caller_key_and_exact_fields():
    header, target, unsigned = _unsigned_checkpoint_for_auth()
    with pytest.raises(ValueError, match="CHECKPOINT_MAC_KEY_MUST_BE_AT_LEAST_32_BYTES"):
        sign_nonce_search_checkpoint(unsigned, header, target, "job-auth", b"short")
    with pytest.raises(ValueError, match="INVALID_UNSIGNED_CHECKPOINT_FIELDS"):
        sign_nonce_search_checkpoint(dict(unsigned, unexpected=True), header, target, "job-auth", _AUTH_TEST_KEY)
    signed = sign_nonce_search_checkpoint(unsigned, header, target, "job-auth", _AUTH_TEST_KEY)
    with pytest.raises(ValueError, match="INVALID_SIGNED_CHECKPOINT_FIELDS"):
        validate_authenticated_nonce_search_checkpoint(dict(signed, unexpected=True), header, target, "job-auth", _AUTH_TEST_KEY)

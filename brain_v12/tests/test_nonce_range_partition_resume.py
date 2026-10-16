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

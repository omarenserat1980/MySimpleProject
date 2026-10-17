import pytest

from brain_v12.brain.bounded_pow_task_engine import (
    MAX_BATCH_HASHES,
    MAX_TASK_HASHES,
    run_bounded_pow_task,
)


def test_task_returns_candidate_without_claiming_submission():
    result = run_bounded_pow_task(
        bytes(80), (1 << 256) - 1, max_total_hashes=1, batch_hashes=1
    )
    assert result.status == "NONCE_FOUND_UNSUBMITTED"
    assert result.nonce == 0
    assert result.hashes_checked == 1
    assert result.pool_contacted is False
    assert result.share_submitted is False
    assert result.pool_acceptance_verified is False
    assert result.revenue_verified is False


def test_hash_budget_is_enforced_across_batches():
    result = run_bounded_pow_task(
        bytes(80), 1, max_total_hashes=5, batch_hashes=2
    )
    assert result.status == "HASH_BUDGET_EXHAUSTED"
    assert result.hashes_checked == 5
    assert result.next_nonce == 5


def test_cancellation_is_checked_between_batches():
    calls = 0

    def cancel_after_one_batch():
        nonlocal calls
        calls += 1
        return calls >= 2

    result = run_bounded_pow_task(
        bytes(80), 1, max_total_hashes=10, batch_hashes=2,
        cancel_requested=cancel_after_one_batch,
    )
    assert result.status == "CANCELLED"
    assert result.hashes_checked == 2
    assert result.next_nonce == 2


def test_nonce_space_exhaustion_does_not_wrap():
    result = run_bounded_pow_task(
        bytes(80), 1, start_nonce=0xFFFFFFFF,
        max_total_hashes=2, batch_hashes=2,
    )
    assert result.status == "NONCE_SPACE_EXHAUSTED"
    assert result.hashes_checked == 1
    assert result.next_nonce == 0x100000000


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_total_hashes": 0}, "MAX_TOTAL_HASHES_OUT_OF_RANGE"),
        ({"max_total_hashes": MAX_TASK_HASHES + 1}, "MAX_TOTAL_HASHES_OUT_OF_RANGE"),
        ({"batch_hashes": 0}, "BATCH_HASHES_OUT_OF_RANGE"),
        ({"batch_hashes": MAX_BATCH_HASHES + 1}, "BATCH_HASHES_OUT_OF_RANGE"),
        ({"timeout_seconds": 0}, "TIMEOUT_SECONDS_OUT_OF_RANGE"),
        ({"timeout_seconds": float("nan")}, "TIMEOUT_SECONDS_OUT_OF_RANGE"),
        ({"timeout_seconds": float("inf")}, "TIMEOUT_SECONDS_OUT_OF_RANGE"),
        ({"timeout_seconds": 3601}, "TIMEOUT_SECONDS_OUT_OF_RANGE"),
    ],
)
def test_invalid_limits_fail_closed(kwargs, message):
    with pytest.raises(ValueError, match=message):
        run_bounded_pow_task(bytes(80), 1, **kwargs)


def test_bad_header_rejected_before_work():
    with pytest.raises(ValueError, match="BITCOIN_HEADER_MUST_BE_80_BYTES"):
        run_bounded_pow_task(b"short", 1)

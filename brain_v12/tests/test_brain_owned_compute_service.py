import pytest

from brain_v12.brain.brain_owned_compute_service import run_bounded_compute_job


def test_bounded_compute_job_returns_unsubmitted_candidate_for_easy_target():
    result = run_bounded_compute_job(bytes(80), (1 << 256) - 1, max_hashes=1, max_seconds=1)
    assert result["status"] == "NONCE_FOUND_UNSUBMITTED"
    assert result["candidate"]["nonce"] == 0
    assert result["hashes_checked"] == 1
    assert result["network_access_performed"] is False
    assert result["pool_contacted"] is False
    assert result["share_submitted"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_bounded_compute_job_exhausts_only_requested_hash_budget():
    result = run_bounded_compute_job(bytes(80), 1, max_hashes=3, max_seconds=1)
    assert result["status"] == "HASH_BUDGET_EXHAUSTED"
    assert result["hashes_checked"] == 3
    assert result["candidate"] is None
    assert result["network_access_performed"] is False


@pytest.mark.parametrize("kwargs", [
    {"max_hashes": 0},
    {"max_hashes": 10_000_001},
    {"max_seconds": 0},
    {"max_seconds": 31},
    {"start_nonce": -1},
])
def test_bounded_compute_job_rejects_out_of_bounds_requests(kwargs):
    with pytest.raises(ValueError):
        run_bounded_compute_job(bytes(80), 1, **kwargs)


def test_bounded_compute_job_rejects_invalid_header_and_target():
    with pytest.raises(ValueError, match="BITCOIN_HEADER_MUST_BE_80_BYTES"):
        run_bounded_compute_job(b"short", 1)
    with pytest.raises(ValueError, match="TARGET_OUT_OF_RANGE"):
        run_bounded_compute_job(bytes(80), 0)

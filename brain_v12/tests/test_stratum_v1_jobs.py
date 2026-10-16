import pytest

from brain_v12.brain.stratum_v1_jobs import (
    ShareLifecycle,
    StratumJob,
    build_coinbase,
    merkle_root_from_coinbase,
)


def sample_notify():
    return [
        "job-1",
        "00" * 32,
        "01020304",
        "aabbccdd",
        ["11" * 32],
        "20000000",
        "1d00ffff",
        "65aa0000",
        True,
    ]


def test_notify_parsing_and_coinbase_construction():
    job = StratumJob.from_notify(sample_notify())
    coinbase = build_coinbase(job, "a1b2", "c3d4", 2)
    assert coinbase == bytes.fromhex("01020304a1b2c3d4aabbccdd")
    assert job.clean_jobs is True


def test_notify_rejects_wrong_field_sizes():
    params = sample_notify()
    params[1] = "00"
    with pytest.raises(ValueError, match="INVALID_LENGTH_PREVHASH"):
        StratumJob.from_notify(params)


def test_merkle_root_returns_32_raw_bytes():
    job = StratumJob.from_notify(sample_notify())
    coinbase = build_coinbase(job, "a1b2", "c3d4", 2)
    root = merkle_root_from_coinbase(coinbase, job.merkle_branch_hex)
    assert isinstance(root, bytes)
    assert len(root) == 32


def test_share_lifecycle_does_not_claim_independent_acceptance():
    lifecycle = ShareLifecycle()
    request_id = lifecycle.register_candidate("job-1", "fingerprint-1")
    response = lifecycle.resolve(request_id, {"id": request_id, "result": True, "error": None})
    assert response["status"] == "POOL_RESPONSE_SAYS_ACCEPTED"
    assert response["pool_acceptance_verified"] is False
    assert "independent_pool_dashboard_or_api_confirmation" in response["evidence_required"]


def test_duplicate_or_unknown_share_response_is_not_accepted():
    lifecycle = ShareLifecycle()
    assert lifecycle.resolve(999, {"id": 999, "result": True})["pool_acceptance_verified"] is False


def test_coinbase_extranonce2_width_is_enforced():
    job = StratumJob.from_notify(sample_notify())
    with pytest.raises(ValueError, match="INVALID_LENGTH_EXTRANONCE2"):
        build_coinbase(job, "a1b2", "c3", 2)


def test_mismatched_response_does_not_consume_pending_share():
    lifecycle = ShareLifecycle()
    request_id = lifecycle.register_candidate("job-1", "fingerprint-1")
    mismatch = lifecycle.resolve(request_id, {"id": request_id + 1, "result": True})
    assert mismatch["status"] == "MALFORMED_OR_MISMATCHED_RESPONSE"
    # The legitimate response can still be correlated after an injected mismatch.
    valid = lifecycle.resolve(request_id, {"id": request_id, "result": True, "error": None})
    assert valid["status"] == "POOL_RESPONSE_SAYS_ACCEPTED"
    assert valid["pool_acceptance_verified"] is False


def test_invalid_response_ids_fail_closed():
    lifecycle = ShareLifecycle()
    assert lifecycle.resolve(True, {"id": True, "result": True})["status"] == "INVALID_RESPONSE_ID"
    assert lifecycle.resolve(0, {"id": 0, "result": True})["status"] == "INVALID_RESPONSE_ID"

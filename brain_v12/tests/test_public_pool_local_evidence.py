"""Conservative classification tests; fixtures are not real mining evidence."""
from brain_v12.brain.public_pool_local_evidence import classify_public_pool_evidence


def test_stratum_work_does_not_imply_accepted_share_or_revenue():
    result = classify_public_pool_evidence(
        miner_log="Stratum session id: 123\nDEBUG: job_id='abc'\nthread 0: 123 hashes, 10.0 khash/s",
        pool_snapshot={"ok": True, "workers_count": 0, "total_accepted_shares_reported": 0},
    )
    assert result["status"] == "STRATUM_CONNECTED_WORK_OBSERVED_SHARES_UNVERIFIED"
    assert result["local_stratum_session_observed"] is True
    assert result["local_work_job_observed"] is True
    assert result["local_hashrate_output_observed"] is True
    assert result["share_acceptance_verified"] is False
    assert result["revenue_verified"] is False


def test_positive_pool_counter_is_activity_not_revenue():
    result = classify_public_pool_evidence(
        pool_snapshot={"ok": True, "workers_count": 1, "total_accepted_shares_reported": 2}
    )
    assert result["status"] == "POOL_SHARE_ACTIVITY_OBSERVED_NOT_REVENUE_PROOF"
    assert result["share_acceptance_verified"] is False
    assert result["payout_verified"] is False
    assert result["revenue_verified"] is False


def test_local_accepted_message_does_not_verify_payout():
    result = classify_public_pool_evidence(miner_log="accepted: 1/1")
    assert result["local_accepted_message_observed"] is True
    assert result["share_acceptance_verified"] is False
    assert result["revenue_verified"] is False


def test_negative_acceptance_phrases_do_not_count_as_acceptance():
    for log in ("not accepted: 0/1", "share not accepted", "rejected: 1/1", "unaccepted share"):
        result = classify_public_pool_evidence(miner_log=log)
        assert result["local_accepted_message_observed"] is False, log
        assert result["share_acceptance_verified"] is False
        assert result["revenue_verified"] is False


def test_pool_aggregate_activity_is_not_per_share_acceptance_proof():
    result = classify_public_pool_evidence(
        pool_snapshot={"ok": True, "workers_count": 1, "total_accepted_shares_reported": 5}
    )
    assert result["pool_activity_reported"] is True
    assert result["share_acceptance_verified"] is False
    assert result["revenue_verified"] is False


def test_malformed_or_synthetic_counters_fail_closed():
    result = classify_public_pool_evidence(
        pool_snapshot={"ok": True, "workers_count": True, "total_accepted_shares_reported": "999"}
    )
    assert result["pool_snapshot_available"] is False
    assert result["share_acceptance_verified"] is False
    assert result["revenue_verified"] is False


def test_no_evidence_stays_unknown():
    result = classify_public_pool_evidence()
    assert result["status"] == "NO_LOCAL_MINER_SESSION_EVIDENCE"
    assert result["share_acceptance_verified"] is False
    assert result["financial_execution_enabled"] is False

import json

from brain_v12.brain.public_pool_evidence_runtime_adapter import (
    evaluate_persisted_public_pool_evidence,
)


def test_adapter_combines_existing_artifacts_without_claiming_revenue(tmp_path):
    log = tmp_path / "miner.log"
    log.write_text(
        "Stratum session id: abc\nDEBUG: job_id=123\nthread 0: 700.00 khash/s\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "pool.json"
    snapshot.write_text(json.dumps({
        "ok": True,
        "workers_count": 0,
        "total_accepted_shares_reported": 0,
    }), encoding="utf-8")

    result = evaluate_persisted_public_pool_evidence(
        miner_log_path=log,
        pool_snapshot_path=snapshot,
    )

    assert result["status"] == "STRATUM_CONNECTED_WORK_OBSERVED_SHARES_UNVERIFIED"
    assert result["local_stratum_session_observed"] is True
    assert result["local_work_job_observed"] is True
    assert result["local_hashrate_output_observed"] is True
    assert result["network_access_performed"] is False
    assert result["miner_started_or_stopped"] is False
    assert result["pool_settings_changed"] is False
    assert result["payout_verified"] is False
    assert result["revenue_verified"] is False
    assert result["brain_runtime_activity_verified"] is False
    assert set(result["input_artifact_sha256"]) == {
        "miner_log_sha256", "pool_snapshot_sha256"
    }


def test_missing_inputs_remain_unknown_not_success():
    result = evaluate_persisted_public_pool_evidence()
    assert result["status"] == "NO_LOCAL_MINER_SESSION_EVIDENCE"
    assert result["pool_snapshot_available"] is False
    assert result["revenue_verified"] is False
    assert result["payout_verified"] is False


def test_rejects_malformed_snapshot(tmp_path):
    snapshot = tmp_path / "pool.json"
    snapshot.write_text("[]", encoding="utf-8")
    try:
        evaluate_persisted_public_pool_evidence(pool_snapshot_path=snapshot)
    except ValueError as exc:
        assert str(exc) == "POOL_SNAPSHOT_MUST_BE_JSON_OBJECT"
    else:
        raise AssertionError("malformed snapshot was accepted")

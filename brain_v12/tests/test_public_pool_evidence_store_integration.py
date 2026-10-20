import json

from brain_v12.brain.evidence_store import EvidenceStore
from brain_v12.brain.public_pool_evidence_runtime_adapter import (
    persist_public_pool_evidence,
)


def test_public_pool_report_is_appended_as_unverified_diagnostic(tmp_path):
    log = tmp_path / "miner.log"
    log.write_text(
        "Stratum session id: example\nDEBUG: job_id=work-1\nthread 0: 700.00 khash/s\n",
        encoding="utf-8",
    )
    snapshot = tmp_path / "pool.json"
    snapshot.write_text(json.dumps({
        "ok": True,
        "workers_count": 0,
        "total_accepted_shares_reported": 0,
    }), encoding="utf-8")
    store = EvidenceStore(tmp_path / "evidence.db")
    try:
        result = persist_public_pool_evidence(
            store,
            "public-pool-check-1",
            miner_log_path=log,
            pool_snapshot_path=snapshot,
            mission_id="mission-1",
            attempt=2,
            phase="diagnostics",
        )
        saved = store.get(result["evidence_id"])
        assert result["kind"] == "public_pool_diagnostic"
        assert result["verification_status"] == "UNVERIFIED"
        assert saved["verification_status"] == "UNVERIFIED"
        assert saved["task_id"] == "public-pool-check-1"
        assert saved["mission_id"] == "mission-1"
        assert saved["attempt"] == 2
        assert saved["phase"] == "diagnostics"
        assert saved["payload"]["status"] == "STRATUM_CONNECTED_WORK_OBSERVED_SHARES_UNVERIFIED"
        assert saved["payload"]["network_access_performed"] is False
        assert saved["payload"]["miner_started_or_stopped"] is False
        assert saved["payload"]["pool_settings_changed"] is False
        assert saved["payload"]["share_acceptance_verified"] is False
        assert saved["payload"]["payout_verified"] is False
        assert saved["payload"]["revenue_verified"] is False
        assert result["financial_execution_enabled"] is False
        assert len(store.for_task("public-pool-check-1")) == 1
    finally:
        store.close()


def test_public_pool_store_integration_rejects_empty_task_id(tmp_path):
    store = EvidenceStore(tmp_path / "evidence.db")
    try:
        try:
            persist_public_pool_evidence(store, "  ")
        except ValueError as exc:
            assert str(exc) == "TASK_ID_REQUIRED"
        else:
            raise AssertionError("empty task ID must be rejected")
        assert store.for_task("") == []
    finally:
        store.close()

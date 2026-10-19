import pytest

from brain_v12.brain.mining_node_api import stratum_adapter_contract_status
from brain_v12.brain.stratum_v1_adapter_contract import (
    StratumV1AdapterContract,
    validate_endpoint,
)


def _authorize(adapter):
    subscribe = adapter.request("mining.subscribe", [])
    assert subscribe["method"] == "mining.subscribe"
    assert adapter.handle_response({"id": subscribe["id"], "result": [[], "00", 4], "error": None})["status"] == "SUBSCRIBED"
    authorize = adapter.request("mining.authorize", [adapter.worker_name, "offline-test-placeholder"])
    assert adapter.handle_response({"id": authorize["id"], "result": True, "error": None})["status"] == "AUTHORIZED"


def _notify(adapter, clean_jobs=False, job_id="job-1"):
    return adapter.handle_notification({
        "id": None,
        "method": "mining.notify",
        "params": [
            job_id, "00" * 32, "0102", "0304", ["11" * 32],
            "20000000", "1d00ffff", "65aa0000", clean_jobs,
        ],
    })


def test_endpoint_validation_requires_tls_and_performs_no_network():
    endpoint = validate_endpoint("pool.example.test", 3333, tls=True)
    assert endpoint == {
        "host": "pool.example.test",
        "port": 3333,
        "tls_required": True,
        "network_access_performed": False,
    }
    with pytest.raises(ValueError, match="STRATUM_TLS_REQUIRED"):
        validate_endpoint("pool.example.test", 3333, tls=False)
    with pytest.raises(ValueError):
        validate_endpoint("pool.example.test/path", 3333, tls=True)


def test_submit_is_blocked_until_authorization_and_job_notification():
    adapter = StratumV1AdapterContract("sim.worker")
    with pytest.raises(ValueError, match="STRATUM_SESSION_NOT_AUTHORIZED"):
        adapter.prepare_share("job-1", "00000000", "65aa0000", "00000000")
    _authorize(adapter)
    with pytest.raises(ValueError, match="UNKNOWN_OR_STALE_JOB"):
        adapter.prepare_share("job-1", "00000000", "65aa0000", "00000000")


def test_share_acceptance_requires_correlated_positive_pool_response():
    adapter = StratumV1AdapterContract("sim.worker")
    _authorize(adapter)
    assert _notify(adapter)["status"] == "JOB_RECEIVED_UNVERIFIED"
    share = adapter.prepare_share("job-1", "00000000", "65aa0000", "00000000")
    assert share["status"] == "SUBMITTED_PENDING_RESPONSE"
    assert share["pool_acceptance_verified"] is False

    result = adapter.handle_response({"id": share["id"], "result": True, "error": None})
    assert result["status"] == "ACCEPTED"
    assert result["pool_acceptance_verified"] is True
    status = adapter.status()
    assert status["network_access_performed"] is False
    assert status["real_mining_verified"] is False
    assert status["share_counts"]["ACCEPTED"] == 1


def test_negative_submit_response_is_rejected_not_accepted():
    adapter = StratumV1AdapterContract("sim.worker")
    _authorize(adapter)
    _notify(adapter)
    share = adapter.prepare_share("job-1", "00000000", "65aa0000", "00000000")
    result = adapter.handle_response({"id": share["id"], "result": False, "error": None})
    assert result["status"] == "REJECTED"
    assert result["pool_acceptance_verified"] is False
    assert adapter.status()["share_counts"]["REJECTED"] == 1


def test_unmatched_responses_and_invalid_fields_fail_closed():
    adapter = StratumV1AdapterContract("sim.worker")
    with pytest.raises(ValueError, match="UNMATCHED_STRATUM_RESPONSE"):
        adapter.handle_response({"id": 999, "result": True, "error": None})
    _authorize(adapter)
    _notify(adapter)
    with pytest.raises(ValueError, match="INVALID_NONCE_LENGTH"):
        adapter.prepare_share("job-1", "00000000", "65aa0000", "00")
    assert adapter.status()["live_transport_enabled"] is False


def test_notify_validates_protocol_fields_and_difficulty_is_positive():
    adapter = StratumV1AdapterContract("sim.worker")
    _notify(adapter, clean_jobs=True)
    with pytest.raises(ValueError, match="INVALID_DIFFICULTY"):
        adapter.handle_notification({"id": None, "method": "mining.set_difficulty", "params": [0]})
    assert adapter.handle_notification({"id": None, "method": "mining.set_difficulty", "params": [1.5]})["difficulty"] == 1.5



def test_api_status_exposes_contract_without_claiming_live_transport():
    status = stratum_adapter_contract_status()
    assert status["status"] == "CONTRACT_ONLY"
    assert status["live_transport_implemented"] is False
    assert status["live_transport_enabled"] is False
    assert status["network_access_performed"] is False
    assert status["share_submission_enabled"] is False
    assert status["real_mining_verified"] is False
    assert status["revenue_verified"] is False



def test_clean_job_keeps_old_pending_share_response_correlated():
    adapter = StratumV1AdapterContract("sim.worker")
    _authorize(adapter)
    _notify(adapter, clean_jobs=False)
    share = adapter.prepare_share("job-1", "00000000", "65aa0000", "00000000")
    _notify(adapter, clean_jobs=True, job_id="job-2")
    # A late response remains associated with its original request even after
    # the old job is no longer valid for preparing new shares.
    response = adapter.handle_response({"id": share["id"], "result": False, "error": None})
    assert response["status"] == "REJECTED"
    assert adapter.status()["share_counts"]["REJECTED"] == 1
    with pytest.raises(ValueError, match="UNKNOWN_OR_STALE_JOB"):
        adapter.prepare_share("job-1", "00000000", "65aa0000", "00000000")



def test_incomplete_response_cannot_be_counted_as_accepted():
    adapter = StratumV1AdapterContract("sim.worker")
    request = adapter.request("mining.subscribe", [])
    with pytest.raises(ValueError, match="INCOMPLETE_STRATUM_RESPONSE"):
        adapter.handle_response({"id": request["id"], "result": [[], "00", 4]})
    assert adapter.status()["subscribed"] is False

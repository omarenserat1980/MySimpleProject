"""Integration tests for the offline Stratum worker cycle."""
import json

import pytest

from brain_v12.brain.stratum_offline_worker_cycle import (
    classify_offline_cycle_response,
    run_offline_worker_cycle,
)
from brain_v12.brain.stratum_v1_jobs import StratumJob
from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


def authorized_session_and_job():
    session = StratumV1Session("account.worker01", "fixture-password")
    subscribe = json.loads(session.request_subscribe())
    session.receive(json.dumps({
        "id": subscribe["id"], "result": [[], "abcd", 2], "error": None
    }))
    authorize = json.loads(session.request_authorize())
    session.receive(json.dumps({
        "id": authorize["id"], "result": True, "error": None
    }))
    params = [
        "fixture-job-1", "00" * 32, "01020304", "aabbccdd", [],
        "20000000", "ffff001d", "65aa0000", True,
    ]
    session.receive(json.dumps({"method": "mining.notify", "params": params}))
    return session, StratumJob.from_notify(params)


def run(session, job, **overrides):
    args = {
        "extranonce2": "c3d4",
        "ntime_hex": "65aa0000",
        "nonce_start": 10,
        "max_attempts": 4,
        "share_target": (1 << 256) - 1,
        "prevhash_dialect_confirmed": True,
    }
    args.update(overrides)
    return run_offline_worker_cycle(session, job, **args)


def test_cycle_searches_and_prepares_share_but_never_sends_it():
    session, job = authorized_session_and_job()
    result = run(session, job)
    assert result["status"] == "CANDIDATE_READY_FOR_TRANSPORT_NOT_SENT"
    assert result["search"]["status"] == "LOCAL_TARGET_MATCH"
    request = result["submit_request"]
    assert request["method"] == "mining.submit"
    assert request["params"] == [
        "account.worker01", job.job_id, "c3d4", "65aa0000",
        result["search"]["candidate"]["nonce_hex"],
    ]
    assert session.pending[request["id"]] == "share"
    assert result["transport_connected"] is False
    assert result["pool_submission_sent"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_cycle_does_not_prepare_submission_when_bounded_range_has_no_match():
    session, job = authorized_session_and_job()
    result = run(session, job, share_target=1, max_attempts=2)
    assert result["status"] == "NO_CANDIDATE_IN_BOUNDED_RANGE"
    assert result["submit_request"] is None
    assert session.pending == {}


def test_cycle_fails_closed_for_unauthorized_session_or_stale_job():
    session, job = authorized_session_and_job()
    session.authorized = False
    with pytest.raises(StratumProtocolError, match="POOL_AUTHORIZATION_REQUIRED"):
        run(session, job)

    session.authorized = True
    session.receive(json.dumps({
        "method": "mining.notify",
        "params": [
            "replacement-job", "00" * 32, "01020304", "aabbccdd", [],
            "20000000", "ffff001d", "65aa0001", True,
        ],
    }))
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        run(session, job)


def test_response_correlation_never_promotes_fixture_to_live_or_revenue_proof():
    session, job = authorized_session_and_job()
    result = run(session, job)
    request_id = result["submit_request"]["id"]
    outcome = classify_offline_cycle_response(
        session, json.dumps({"id": request_id, "result": True, "error": None})
    )
    assert outcome["pool_reported_acceptance"] is True
    assert outcome["live_transport_verified"] is False
    assert outcome["independent_share_validation_verified"] is False
    assert outcome["payout_verified"] is False
    assert outcome["revenue_verified"] is False

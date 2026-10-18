"""Tests for session-bound difficulty offline Stratum cycle."""
import json

import pytest

from brain_v12.brain.stratum_difficulty_target import DIFFICULTY_ONE_TARGET
from brain_v12.brain.stratum_difficulty_worker_cycle import (
    run_difficulty_bound_offline_cycle,
)
from brain_v12.brain.stratum_v1_jobs import StratumJob
from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


def authorized_session_and_job(difficulty="1"):
    session = StratumV1Session("account.worker01", "fixture-password")
    subscribe = json.loads(session.request_subscribe())
    session.receive(json.dumps({
        "id": subscribe["id"], "result": [[], "abcd", 2], "error": None
    }))
    authorize = json.loads(session.request_authorize())
    session.receive(json.dumps({
        "id": authorize["id"], "result": True, "error": None
    }))
    session.receive(json.dumps({
        "id": None, "method": "mining.set_difficulty", "params": [difficulty]
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
        "prevhash_dialect_confirmed": True,
    }
    args.update(overrides)
    return run_difficulty_bound_offline_cycle(session, job, **args)


def test_session_difficulty_one_target_is_used_for_offline_search():
    session, job = authorized_session_and_job("1")
    result = run(session, job)
    assert result["difficulty_target"]["share_target"] == DIFFICULTY_ONE_TARGET
    assert result["search"]["candidate"]["share_target"] == DIFFICULTY_ONE_TARGET
    assert result["evidence_class"] == "OFFLINE_SESSION_DIFFICULTY_BOUND_STRATUM_WORKER_CYCLE"
    assert result["difficulty_bound_to_validated_session_state"] is True
    assert result["difficulty_provenance_independently_verified"] is False
    assert result["transport_connected"] is False
    assert result["pool_submission_sent"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_session_difficulty_two_halves_target():
    session, job = authorized_session_and_job("2")
    result = run(session, job)
    assert result["difficulty_target"]["share_target"] == DIFFICULTY_ONE_TARGET // 2
    assert result["search"]["candidate"]["share_target"] == DIFFICULTY_ONE_TARGET // 2


def test_missing_session_difficulty_fails_closed_before_search():
    session, job = authorized_session_and_job()
    session.difficulty = None
    with pytest.raises(StratumProtocolError, match="SESSION_DIFFICULTY_REQUIRED"):
        run(session, job)
    assert session.pending == {}


def test_no_local_match_does_not_prepare_a_share_request():
    session, job = authorized_session_and_job("1e80")
    result = run(session, job)
    assert result["status"] == "NO_CANDIDATE_IN_BOUNDED_RANGE"
    assert result["submit_request"] is None
    assert session.pending == {}
    assert result["pool_submission_sent"] is False

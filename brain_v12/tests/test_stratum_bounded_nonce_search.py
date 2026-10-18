"""Offline tests for bounded Stratum nonce search."""
import json
import pytest

from brain_v12.brain.stratum_bounded_nonce_search import (
    MAX_NONCE_ATTEMPTS,
    search_session_nonce_range,
)
from brain_v12.brain.stratum_v1_jobs import StratumJob
from brain_v12.brain.stratum_v1_protocol import StratumV1Session


def authorized_session_and_job():
    session = StratumV1Session("account.worker01", "test-password")
    session.request_subscribe()
    session.receive(json.dumps({
        "id": 1, "result": [[], "abcd", 2], "error": None
    }))
    session.request_authorize()
    session.receive(json.dumps({"id": 2, "result": True, "error": None}))
    params = [
        "job-42", "00" * 32, "01020304", "aabbccdd", ["11" * 32],
        "20000000", "ffff001d", "65aa0000", True,
    ]
    session.receive(json.dumps({"method": "mining.notify", "params": params}))
    return session, StratumJob.from_notify(params)


def search(session, job, **overrides):
    args = {
        "extranonce2": "c3d4",
        "ntime_hex": "65aa0000",
        "nonce_start": 42,
        "max_attempts": 3,
        "share_target": 2**256 - 1,
        "prevhash_dialect_confirmed": True,
    }
    args.update(overrides)
    return search_session_nonce_range(session, job, **args)


def test_finds_first_nonce_within_bounded_range():
    session, job = authorized_session_and_job()
    result = search(session, job)
    assert result["status"] == "LOCAL_TARGET_MATCH"
    assert result["attempts"] == 1
    assert result["nonce_found"] == 42
    assert result["candidate"]["nonce_hex"] == "0000002a"
    assert result["pool_submission_sent"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_returns_no_match_when_target_is_below_every_tested_hash():
    session, job = authorized_session_and_job()
    result = search(session, job, max_attempts=2, share_target=1)
    assert result["status"] == "NO_LOCAL_TARGET_MATCH_IN_RANGE"
    assert result["attempts"] == 2
    assert result["nonce_found"] is None
    assert result["pool_acceptance_verified"] is False
    assert result["revenue_verified"] is False


@pytest.mark.parametrize("attempts", [0, -1, MAX_NONCE_ATTEMPTS + 1, True, "2"])
def test_rejects_invalid_or_unbounded_attempt_count(attempts):
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match="MAX_ATTEMPTS"):
        search(session, job, max_attempts=attempts)


@pytest.mark.parametrize(
    ("start", "attempts", "code"),
    [
        (-1, 1, "NONCE_START_OUT_OF_RANGE"),
        (True, 1, "INVALID_NONCE_START"),
        (0xFFFFFFFF, 2, "NONCE_RANGE_OVERFLOWS_UINT32"),
    ],
)
def test_rejects_invalid_or_wrapping_nonce_range(start, attempts, code):
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match=code):
        search(session, job, nonce_start=start, max_attempts=attempts)


def test_requires_explicit_prevhash_dialect_confirmation():
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match="STRATUM_PREVHASH_DIALECT_NOT_CONFIRMED"):
        search(session, job, prevhash_dialect_confirmed=False)

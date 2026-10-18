"""Offline tests for session-bound Stratum Bitcoin header candidates."""
import json
import pytest

from brain_v12.brain.stratum_session_header_candidate import build_session_header_candidate
from brain_v12.brain.stratum_v1_jobs import StratumJob
from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


def sample_notify():
    return [
        "job-42",
        "00" * 32,
        "01020304",
        "aabbccdd",
        ["11" * 32],
        "20000000",
        "ffff001d",
        "65aa0000",
        True,
    ]


def authorized_session_and_job():
    session = StratumV1Session("account.worker01", "test-password")
    session.request_subscribe()
    session.receive(json.dumps({
        "id": 1, "result": [[], "abcd", 2], "error": None
    }))
    session.request_authorize()
    session.receive(json.dumps({"id": 2, "result": True, "error": None}))
    params = sample_notify()
    session.receive(json.dumps({"method": "mining.notify", "params": params}))
    return session, StratumJob.from_notify(params)


def test_builds_80_byte_candidate_and_does_not_claim_live_mining():
    session, job = authorized_session_and_job()
    result = build_session_header_candidate(
        session, job, extranonce2="c3d4", ntime_hex="65aa0000",
        nonce_hex="0000002a", share_target=2**256 - 1,
        prevhash_dialect_confirmed=True,
    )
    assert result["header_bytes"] == 80
    assert len(bytes.fromhex(result["header_hex"])) == 80
    assert result["nonce_hex"] == "0000002a"
    assert result["meets_supplied_share_target"] is True
    assert result["evidence_class"] == "OFFLINE_SESSION_BOUND_HEADER_CANDIDATE"
    assert result["pool_submission_sent"] is False
    assert result["pool_acceptance_verified"] is False
    assert result["real_mining_verified"] is False
    assert result["revenue_verified"] is False


def test_requires_explicit_prevhash_dialect_confirmation():
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match="STRATUM_PREVHASH_DIALECT_NOT_CONFIRMED"):
        build_session_header_candidate(
            session, job, extranonce2="c3d4", ntime_hex="65aa0000",
            nonce_hex="0000002a", share_target=2**256 - 1,
        )


def test_rejects_unauthorized_session_and_stale_job():
    session, job = authorized_session_and_job()
    session.authorized = False
    with pytest.raises(StratumProtocolError, match="POOL_AUTHORIZATION_REQUIRED"):
        build_session_header_candidate(
            session, job, extranonce2="c3d4", ntime_hex="65aa0000",
            nonce_hex="0000002a", share_target=2**256 - 1,
            prevhash_dialect_confirmed=True,
        )
    session.authorized = True
    session.current_job_id = "job-new"
    with pytest.raises(StratumProtocolError, match="JOB_DOES_NOT_MATCH_CURRENT_SESSION"):
        build_session_header_candidate(
            session, job, extranonce2="c3d4", ntime_hex="65aa0000",
            nonce_hex="0000002a", share_target=2**256 - 1,
            prevhash_dialect_confirmed=True,
        )


@pytest.mark.parametrize("nonce", ["xyz0002a", "0000002", "0000002g", 42])
def test_rejects_invalid_nonce_hex(nonce):
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match="INVALID_NONCE_HEX"):
        build_session_header_candidate(
            session, job, extranonce2="c3d4", ntime_hex="65aa0000",
            nonce_hex=nonce, share_target=2**256 - 1,
            prevhash_dialect_confirmed=True,
        )


def test_rejects_extranonce2_wrong_negotiated_width():
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match="INVALID_LENGTH_EXTRANONCE2"):
        build_session_header_candidate(
            session, job, extranonce2="c3", ntime_hex="65aa0000",
            nonce_hex="0000002a", share_target=2**256 - 1,
            prevhash_dialect_confirmed=True,
        )


def test_rejects_invalid_share_target():
    session, job = authorized_session_and_job()
    with pytest.raises(ValueError, match="SHARE_TARGET_OUT_OF_RANGE"):
        build_session_header_candidate(
            session, job, extranonce2="c3d4", ntime_hex="65aa0000",
            nonce_hex="0000002a", share_target=0,
            prevhash_dialect_confirmed=True,
        )

"""Fail-closed regression tests for Stratum V1 session state.

All messages are in-memory fixtures; these tests never open a network connection.
"""
import json

import pytest

from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


def wire(payload):
    return json.dumps(payload, separators=(",", ":")) + "\n"


def notify(job_id, clean_jobs):
    return {
        "id": None,
        "method": "mining.notify",
        "params": [
            job_id, "00" * 32, "01020304", "aabbccdd", [],
            "20000000", "1d00ffff", "65aa0000", clean_jobs,
        ],
    }


def authorized_session():
    session = StratumV1Session("fixture.worker", "fixture-password")
    subscribe = json.loads(session.request_subscribe())
    session.receive(wire({
        "id": subscribe["id"], "result": [[], "abcd", 2], "error": None,
    }))
    authorize = json.loads(session.request_authorize())
    session.receive(wire({
        "id": authorize["id"], "result": True, "error": None,
    }))
    session.receive(wire(notify("job-old", False)))
    return session


def test_clean_jobs_invalidates_old_job_for_submission():
    session = authorized_session()
    session.receive(wire(notify("job-new", True)))

    assert session.current_job_id == "job-new"
    assert "job-old" not in session.active_job_ids
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        session.request_submit("job-old", "0000", "65aa0000", "00000001")


def test_malformed_response_does_not_consume_pending_request():
    session = StratumV1Session("fixture.worker", "fixture-password")
    request = json.loads(session.request_subscribe())

    with pytest.raises(StratumProtocolError, match="MALFORMED_JSON_RPC_RESPONSE"):
        session.receive(wire({"id": request["id"], "result": [[], "abcd", 2]}))

    assert session.pending[request["id"]] == "subscribe"
    assert not session.subscribed


def test_malformed_authorize_result_does_not_authorize_session():
    session = StratumV1Session("fixture.worker", "fixture-password")
    subscribe = json.loads(session.request_subscribe())
    session.receive(wire({
        "id": subscribe["id"], "result": [[], "abcd", 2], "error": None,
    }))
    authorize = json.loads(session.request_authorize())

    with pytest.raises(StratumProtocolError, match="MALFORMED_AUTHORIZE_RESPONSE"):
        session.receive(wire({
            "id": authorize["id"], "result": "true", "error": None,
        }))

    assert session.pending[authorize["id"]] == "authorize"
    assert not session.authorized

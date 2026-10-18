"""Additional in-memory Stratum state regressions; no network access."""
import json

import pytest

from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


def wire(value):
    return json.dumps(value, separators=(",", ":")) + "\n"


def test_invalid_set_extranonce_does_not_overwrite_valid_state():
    session = StratumV1Session("fixture.worker", "fixture-password")
    session.receive(wire({
        "id": None, "method": "mining.set_extranonce", "params": ["abcd", 2],
    }))

    with pytest.raises(StratumProtocolError, match="INVALID_EXTRANONCE"):
        session.receive(wire({
            "id": None, "method": "mining.set_extranonce", "params": ["not-hex", 3],
        }))

    assert session.extranonce1_hex == "abcd"
    assert session.extranonce2_size == 2


def test_pool_rejection_consumes_only_matching_share_request():
    session = StratumV1Session("fixture.worker", "fixture-password")
    session.subscribed = True
    session.authorized = True
    session.current_job_id = "job-1"
    session.active_job_ids.add("job-1")
    request = json.loads(session.request_submit(
        "job-1", "aabb", "65aa0000", "00000001"
    ))

    outcome = session.receive(wire({
        "id": request["id"],
        "result": False,
        "error": [23, "low difficulty share", None],
    }))

    assert outcome["event"] == "SHARE_RESPONSE"
    assert outcome["status"] == "REJECTED_BY_POOL"
    assert session.rejected_shares == 1
    assert request["id"] not in session.pending
    assert session.accepted_shares == 0


def test_unmatched_response_cannot_consume_any_pending_request():
    session = StratumV1Session("fixture.worker", "fixture-password")
    request = json.loads(session.request_subscribe())

    with pytest.raises(StratumProtocolError, match="UNMATCHED_RESPONSE_ID"):
        session.receive(wire({
            "id": request["id"] + 99, "result": [], "error": None,
        }))

    assert session.pending[request["id"]] == "subscribe"
    assert not session.subscribed

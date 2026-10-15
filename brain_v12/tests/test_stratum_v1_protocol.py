"""Protocol tests for the fail-closed Stratum V1 state machine."""
import json
import pytest

from brain_v12.brain.stratum_v1_protocol import (
    StratumProtocolError, StratumV1Session, encode_request, parse_message,
)


def test_request_is_newline_delimited_json_rpc():
    payload = encode_request(1, "mining.subscribe", ["test"])
    assert payload.endswith(b"\n")
    assert json.loads(payload) == {"id": 1, "method": "mining.subscribe", "params": ["test"]}


def test_subscription_authorization_and_share_acceptance_are_distinct():
    session = StratumV1Session("worker.1", "secret")
    sub = json.loads(session.request_subscribe())
    assert sub["method"] == "mining.subscribe"
    session.receive(json.dumps({"id": sub["id"], "result": [[], "abcd", 4], "error": None}))
    assert session.subscribed and not session.authorized
    auth = json.loads(session.request_authorize())
    assert auth["params"] == ["worker.1", "secret"]
    session.receive(json.dumps({"id": auth["id"], "result": True, "error": None}))
    assert session.authorized
    session.receive(json.dumps({"id": None, "method": "mining.notify",
                                "params": ["job-1", "prev", "cb1", "cb2", [], "v", "b", "t", True]}))
    share = json.loads(session.request_submit("job-1", "00000001", "65a1b2c3", "00000001"))
    assert share["method"] == "mining.submit"
    result = session.receive(json.dumps({"id": share["id"], "result": True, "error": None}))
    assert result["status"] == "ACCEPTED_BY_POOL"
    assert session.snapshot()["real_bitcoin_mining"] is False


def test_authorization_cannot_happen_before_subscription():
    session = StratumV1Session("worker", "secret")
    with pytest.raises(StratumProtocolError, match="SUBSCRIBE_REQUIRED"):
        session.request_authorize()


def test_share_requires_authorization_and_current_job():
    session = StratumV1Session("worker", "secret")
    with pytest.raises(StratumProtocolError, match="POOL_AUTHORIZATION_REQUIRED"):
        session.request_submit("job", "00", "00", "00")


def test_unknown_or_stale_job_is_rejected():
    session = StratumV1Session("worker", "secret", subscribed=True, authorized=True,
                               current_job_id="job-2")
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        session.request_submit("job-1", "00", "00", "00")


@pytest.mark.parametrize("line", ["{", "[]", "null", "x" * 1_000_001])
def test_malformed_messages_fail_closed(line):
    with pytest.raises(StratumProtocolError):
        parse_message(line)


def test_invalid_difficulty_is_rejected():
    session = StratumV1Session("worker", "secret")
    with pytest.raises(StratumProtocolError, match="INVALID_DIFFICULTY"):
        session.receive(json.dumps({"id": None, "method": "mining.set_difficulty", "params": [0]}))


def test_pool_rejection_is_not_counted_as_acceptance():
    session = StratumV1Session("worker", "secret", authorized=True, current_job_id="job")
    request = json.loads(session.request_submit("job", "00", "00", "00"))
    result = session.receive(json.dumps({"id": request["id"], "result": False, "error": [20, "bad share", None]}))
    assert result["status"] == "REJECTED_BY_POOL"
    assert session.accepted_shares == 0
    assert session.rejected_shares == 1

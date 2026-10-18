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
                                "params": ["job-1", "00" * 32, "01020304", "aabbccdd", [],
                                           "20000000", "1d00ffff", "65aa0000", True]}))
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
        session.request_submit("job", "00", "00000000", "00000000")


def test_unknown_or_stale_job_is_rejected():
    session = StratumV1Session("worker", "secret", subscribed=True, authorized=True,
                               current_job_id="job-2")
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        session.request_submit("job-1", "00", "00000000", "00000000")


@pytest.mark.parametrize("job_id", [None, "", 7, [], {}])
def test_malformed_submit_job_identifiers_fail_closed(job_id):
    session = StratumV1Session("worker", "secret", authorized=True, current_job_id="job")
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        session.request_submit(job_id, "00000001", "00000000", "00000000")
    assert not session.pending


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
    request = json.loads(session.request_submit("job", "00", "00000000", "00000000"))
    result = session.receive(json.dumps({"id": request["id"], "result": False, "error": [20, "bad share", None]}))
    assert result["status"] == "REJECTED_BY_POOL"
    assert session.accepted_shares == 0
    assert session.rejected_shares == 1


def test_malformed_share_response_does_not_consume_pending_request():
    session = StratumV1Session("worker", "secret", authorized=True, current_job_id="job")
    request = json.loads(session.request_submit("job", "00", "00000000", "00000000"))
    with pytest.raises(StratumProtocolError, match="MALFORMED_JSON_RPC_RESPONSE"):
        session.receive(json.dumps({"id": request["id"], "result": True}))
    assert request["id"] in session.pending
    result = session.receive(json.dumps({"id": request["id"], "result": True, "error": None}))
    assert result["status"] == "ACCEPTED_BY_POOL"
    assert request["id"] not in session.pending


def test_malformed_subscribe_response_does_not_consume_pending_request():
    session = StratumV1Session("worker", "secret")
    request = json.loads(session.request_subscribe())
    with pytest.raises(StratumProtocolError, match="MALFORMED_SUBSCRIBE_RESPONSE"):
        session.receive(json.dumps({"id": request["id"], "result": [], "error": None}))
    assert request["id"] in session.pending
    session.receive(json.dumps({"id": request["id"], "result": [[], "abcd", 4], "error": None}))
    assert session.subscribed is True
    assert request["id"] not in session.pending


def test_invalid_authorize_result_does_not_consume_pending_request():
    session = StratumV1Session("worker", "secret", subscribed=True)
    request = json.loads(session.request_authorize())
    with pytest.raises(StratumProtocolError, match="MALFORMED_AUTHORIZE_RESPONSE"):
        session.receive(json.dumps({"id": request["id"], "result": "true", "error": None}))
    assert request["id"] in session.pending
    session.receive(json.dumps({"id": request["id"], "result": True, "error": None}))
    assert session.authorized is True


@pytest.mark.parametrize("params", [
    ["job", "00", "0102", "0304", [], "20000000", "1d00ffff", "65aa0000", True],
    ["job", "0000000000000000000000000000000000000000000000000000000000000000", "0102", "0304", [], "20000000", "1d00ffff", "65aa0000"],
    ["job", "0000000000000000000000000000000000000000000000000000000000000000", "0102", "0304", [], "20000000", "1d00ffff", "65aa0000", "true"],
])
def test_malformed_notify_jobs_are_rejected_without_advancing_current_job(params):
    session = StratumV1Session("worker", "secret", current_job_id="previous-job")
    with pytest.raises(StratumProtocolError, match="INVALID_MINING_JOB"):
        session.receive(json.dumps({"id": None, "method": "mining.notify", "params": params}))
    assert session.current_job_id == "previous-job"


@pytest.mark.parametrize(
    ("field_index", "bad_value", "error"),
    [
        (1, "00" * 16 + "  " + "00" * 16, "INVALID_HEX_PREVHASH"),
        (2, "0102  ", "INVALID_HEX_COINBASE1"),
        (3, "aabb  ", "INVALID_HEX_COINBASE2"),
        (4, None, "INVALID_HEX_MERKLE_BRANCH"),
        (5, "20 000000", "INVALID_HEX_VERSION"),
        (6, "1d00 ff ", "INVALID_HEX_NBITS"),
        (7, "65aa 0000", "INVALID_HEX_NTIME"),
    ],
)
def test_notify_rejects_embedded_or_trailing_hex_whitespace(field_index, bad_value, error):
    params = ["job-1", "00" * 32, "01020304", "aabbccdd", ["11" * 32],
              "20000000", "1d00ffff", "65aa0000", True]
    if field_index == 4:
        params[4] = ["11" * 16 + "  " + "11" * 16]
    else:
        params[field_index] = bad_value
    session = StratumV1Session("worker", "secret")
    with pytest.raises(StratumProtocolError, match="INVALID_MINING_JOB"):
        session.receive(json.dumps({"id": None, "method": "mining.notify", "params": params}))
    assert session.current_job_id is None


@pytest.mark.parametrize(
    ("extranonce1", "extranonce2", "error"),
    [
        ("a1b2  ", "c3d4", "INVALID_HEX_EXTRANONCE1"),
        ("a1b2", "c3d4  ", "INVALID_HEX_EXTRANONCE2"),
    ],
)
def test_coinbase_rejects_noncanonical_extranonce_hex(extranonce1, extranonce2, error):
    from brain_v12.brain.stratum_v1_jobs import StratumJob, build_coinbase
    job = StratumJob.from_notify(
        ["job-1", "00" * 32, "01020304", "aabbccdd", ["11" * 32],
         "20000000", "1d00ffff", "65aa0000", True]
    )
    with pytest.raises(ValueError, match=error):
        build_coinbase(job, extranonce1, extranonce2, 2)


def test_share_submit_requires_exact_ntime_and_nonce_widths():
    session = StratumV1Session("worker", "secret", authorized=True, current_job_id="job")
    for ntime, nonce, expected in [
        ("0000000", "00000001", "INVALID_NTIME_HEX_WIDTH"),
        ("000000000", "00000001", "INVALID_NTIME_HEX_WIDTH"),
        ("00000000", "0000000", "INVALID_NONCE_HEX_WIDTH"),
        ("00000000", "000000000", "INVALID_NONCE_HEX_WIDTH"),
        ("0000000g", "00000001", "INVALID_NTIME_HEX_WIDTH"),
        ("00000000", "0000000g", "INVALID_NONCE_HEX_WIDTH"),
    ]:
        with pytest.raises(StratumProtocolError, match=expected):
            session.request_submit("job", "00000001", ntime, nonce)
    assert not session.pending


@pytest.mark.parametrize("extranonce2", ["", "0", "gg", "00" * 33])
def test_share_submit_rejects_invalid_or_oversized_extranonce2(extranonce2):
    session = StratumV1Session("worker", "secret", authorized=True, current_job_id="job")
    with pytest.raises(StratumProtocolError, match="INVALID_EXTRANONCE2_HEX_WIDTH"):
        session.request_submit("job", extranonce2, "00000000", "00000000")
    assert not session.pending


@pytest.mark.parametrize(
    ("extranonce1", "extranonce2_size", "expected_error"),
    [
        ("a1b", 4, "MALFORMED_SUBSCRIBE_EXTRANONCE1"),
        ("zzzz", 4, "MALFORMED_SUBSCRIBE_EXTRANONCE1"),
        ("00" * 65, 4, "MALFORMED_SUBSCRIBE_EXTRANONCE1"),
        ("abcd", True, "MALFORMED_SUBSCRIBE_EXTRANONCE2_SIZE"),
        ("abcd", 0, "MALFORMED_SUBSCRIBE_EXTRANONCE2_SIZE"),
        ("abcd", 33, "MALFORMED_SUBSCRIBE_EXTRANONCE2_SIZE"),
    ],
)
def test_invalid_subscribe_extranonce_parameters_do_not_consume_request(
    extranonce1, extranonce2_size, expected_error
):
    session = StratumV1Session("worker", "secret")
    request = json.loads(session.request_subscribe())
    response = {"id": request["id"], "result": [[], extranonce1, extranonce2_size], "error": None}
    with pytest.raises(StratumProtocolError, match=expected_error):
        session.receive(json.dumps(response))
    assert request["id"] in session.pending
    assert session.subscribed is False
    assert session.extranonce1_hex is None
    assert session.extranonce2_size is None


def test_valid_subscribe_stores_normalized_extranonce_parameters():
    session = StratumV1Session("worker", "secret")
    request = json.loads(session.request_subscribe())
    session.receive(json.dumps({
        "id": request["id"], "result": [[], "A1B2", 4], "error": None
    }))
    assert session.subscribed is True
    assert session.extranonce1_hex == "a1b2"
    assert session.extranonce2_size == 4
    snapshot = session.snapshot()
    assert snapshot["extranonce1_configured"] is True
    assert snapshot["extranonce2_size"] == 4
    assert "extranonce1_hex" not in snapshot


@pytest.mark.parametrize(
    ("params", "expected_error"),
    [
        (["a1b", 4], "INVALID_EXTRANONCE1_HEX"),
        (["zzzz", 4], "INVALID_EXTRANONCE1_HEX"),
        (["00" * 65, 4], "INVALID_EXTRANONCE1_HEX"),
        (["abcd", True], "INVALID_EXTRANONCE2_SIZE"),
        (["abcd", 0], "INVALID_EXTRANONCE2_SIZE"),
        (["abcd", 33], "INVALID_EXTRANONCE2_SIZE"),
        (["abcd"], "INVALID_EXTRANONCE"),
    ],
)
def test_set_extranonce_notification_rejects_invalid_fields_without_mutation(params, expected_error):
    session = StratumV1Session("worker", "secret", extranonce1_hex="beef", extranonce2_size=2)
    before = (session.extranonce1_hex, session.extranonce2_size)
    with pytest.raises(StratumProtocolError, match=expected_error):
        session.receive(json.dumps({
            "id": None, "method": "mining.set_extranonce", "params": params
        }))
    assert (session.extranonce1_hex, session.extranonce2_size) == before


def test_set_extranonce_notification_updates_only_after_full_validation():
    session = StratumV1Session("worker", "secret", extranonce1_hex="beef", extranonce2_size=2)
    session.receive(json.dumps({
        "id": None, "method": "mining.set_extranonce", "params": ["A1B2", 8]
    }))
    assert session.extranonce1_hex == "a1b2"
    assert session.extranonce2_size == 8

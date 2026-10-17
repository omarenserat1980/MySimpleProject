"""Deterministic in-memory fake Stratum server/session lifecycle tests.

This fake speaks JSON-RPC messages in-process. It opens no sockets, reads no
credentials from the environment, and cannot connect to a real mining pool.
"""
from __future__ import annotations

import json

import pytest

from brain_v12.brain.stratum_v1_offline_candidate import (
    LEGACY_PREVHASH_DIALECT,
    build_offline_stratum_candidate,
)
from brain_v12.brain.stratum_v1_protocol import StratumProtocolError, StratumV1Session


def notify(job_id: str, *, clean: bool = True) -> dict:
    return {
        "id": None,
        "method": "mining.notify",
        "params": [
            job_id,
            "00" * 32,
            "01020304",
            "aabbccdd",
            [],
            "20000000",
            "1d00ffff",
            "65aa0000",
            clean,
        ],
    }


class FakeStratumServer:
    """Small deterministic peer; it only exchanges in-memory JSON messages."""

    def __init__(self) -> None:
        self.authorized_users: set[str] = set()
        self.submitted: list[list[str]] = []
        self.reject_next_share = False

    def handle(self, request_bytes: bytes) -> bytes:
        request = json.loads(request_bytes.decode("utf-8"))
        method = request["method"]
        params = request["params"]
        if method == "mining.subscribe":
            result = [[], "a1b2", 4]
            error = None
        elif method == "mining.authorize":
            username, password = params
            if username and password == "test-only-password":
                self.authorized_users.add(username)
                result, error = True, None
            else:
                result, error = False, [24, "unauthorized", None]
        elif method == "mining.submit":
            username, job_id, extranonce2, ntime, nonce = params
            if username not in self.authorized_users:
                result, error = False, [24, "unauthorized", None]
            elif self.reject_next_share:
                self.reject_next_share = False
                result, error = False, [20, "stale or invalid share", None]
            else:
                self.submitted.append([username, job_id, extranonce2, ntime, nonce])
                result, error = True, None
        else:
            result, error = None, [ method, "unsupported method", None ]
        return (json.dumps({"id": request["id"], "result": result, "error": error})
                + "\n").encode("utf-8")


def exchange(session: StratumV1Session, server: FakeStratumServer, request: bytes) -> dict:
    response = server.handle(request)
    return session.receive(response)


def test_fake_server_subscription_authorization_and_job_lifecycle_are_offline():
    server = FakeStratumServer()
    session = StratumV1Session("worker-test", "test-only-password")

    subscribe = session.request_subscribe()
    exchange(session, server, subscribe)
    assert session.subscribed is True
    assert session.authorized is False

    authorize = session.request_authorize()
    exchange(session, server, authorize)
    assert session.authorized is True

    session.receive(json.dumps(notify("job-001")))
    assert session.current_job_id == "job-001"

    session.receive(json.dumps({
        "id": None, "method": "mining.set_difficulty", "params": [2.5]
    }))
    assert session.difficulty == 2.5

    # A malformed job must not replace the last valid job.
    malformed = notify("bad-job")
    malformed["params"][1] = "00"
    with pytest.raises(StratumProtocolError, match="INVALID_MINING_JOB"):
        session.receive(json.dumps(malformed))
    assert session.current_job_id == "job-001"

    # A valid new job supersedes the old job; stale submissions are blocked.
    session.receive(json.dumps(notify("job-002", clean=True)))
    assert session.current_job_id == "job-002"
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        session.request_submit("job-001", "00000001", "65aa0000", "00000001")

    snapshot = session.snapshot()
    assert snapshot["transport_connected"] is False
    assert snapshot["real_bitcoin_mining"] is False
    assert snapshot["revenue_verified"] is False
    assert "password" not in json.dumps(snapshot).lower()
    assert server.submitted == []


def test_fake_server_rejection_and_acceptance_are_only_simulated_responses():
    server = FakeStratumServer()
    session = StratumV1Session(
        "worker-test", "test-only-password", subscribed=True, authorized=True,
        current_job_id="job-001",
    )
    server.authorized_users.add("worker-test")

    server.reject_next_share = True
    rejected_request = session.request_submit(
        "job-001", "00000001", "65aa0000", "00000001"
    )
    rejected = exchange(session, server, rejected_request)
    assert rejected["status"] == "REJECTED_BY_POOL"
    assert session.rejected_shares == 1
    assert session.accepted_shares == 0
    assert server.submitted == []

    accepted_request = session.request_submit(
        "job-001", "00000002", "65aa0000", "00000002"
    )
    accepted = exchange(session, server, accepted_request)
    assert accepted["status"] == "ACCEPTED_BY_POOL"
    assert session.accepted_shares == 1
    assert len(server.submitted) == 1

    # A duplicate response cannot be correlated to a pending request.
    with pytest.raises(StratumProtocolError, match="UNMATCHED_RESPONSE_ID"):
        session.receive(json.dumps({"id": json.loads(accepted_request)["id"],
                                      "result": True, "error": None}))

    assert session.snapshot()["transport_connected"] is False
    assert session.snapshot()["real_bitcoin_mining"] is False
    assert session.snapshot()["revenue_verified"] is False


def test_fake_reconnect_notification_requires_action_and_does_not_connect():
    session = StratumV1Session("worker-test", "test-only-password")
    event = session.receive(json.dumps({
        "id": None, "method": "client.reconnect", "params": []
    }))
    assert event == {"event": "RECONNECT_REQUESTED", "action_required": True}
    assert session.snapshot()["transport_connected"] is False



def test_session_job_and_bitcoin_header_candidate_stay_correlated_offline():
    session = StratumV1Session(
        "worker-test", "test-only-password", subscribed=True, authorized=True,
    )
    first = notify("job-before")
    session.receive(json.dumps(first))
    # Stratum notify version/nbits/ntime are converted explicitly to serialized
    # header byte order; the candidate builder never guesses these fields.
    candidate = build_offline_stratum_candidate(
        first["params"],
        extranonce1_hex="a1b2",
        extranonce2_hex="c3d4",
        extranonce2_size=2,
        version_header_hex=bytes.fromhex(first["params"][5])[::-1].hex(),
        ntime_header_hex=bytes.fromhex(first["params"][7])[::-1].hex(),
        nbits_header_hex=bytes.fromhex(first["params"][6])[::-1].hex(),
        nonce=0,
        share_target=(1 << 256) - 1,
        prevhash_dialect=LEGACY_PREVHASH_DIALECT,
    )
    assert candidate["job_id"] == session.current_job_id == "job-before"
    assert candidate["header_bytes"] == 80
    assert candidate["share_target_met"] is True
    assert candidate["share_submitted"] is False
    assert candidate["pool_acceptance_verified"] is False

    # clean_jobs=true invalidates the previous job for new share submissions.
    second = notify("job-after", clean=True)
    session.receive(json.dumps(second))
    assert session.current_job_id == "job-after"
    with pytest.raises(StratumProtocolError, match="UNKNOWN_OR_STALE_JOB"):
        session.request_submit("job-before", "00000001", "65aa0000", "00000001")
    assert session.snapshot()["real_bitcoin_mining"] is False
    assert session.snapshot()["revenue_verified"] is False

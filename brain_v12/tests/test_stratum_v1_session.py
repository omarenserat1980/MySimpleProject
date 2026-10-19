import json

import pytest

from brain_v12.brain.stratum_v1_session import StratumV1Session
from brain_v12.brain.stratum_v1_tls_transport import (
    StratumTransportError,
    StratumV1TLSTransport,
)


class FakeSocket:
    def __init__(self, incoming=b""):
        self.incoming = bytearray(incoming)
        self.sent = []
        self.closed = False

    def settimeout(self, timeout):
        self.timeout = timeout

    def sendall(self, payload):
        self.sent.append(payload)

    def recv(self, count):
        if not self.incoming:
            return b""
        chunk = bytes(self.incoming[:count])
        del self.incoming[:count]
        return chunk

    def close(self):
        self.closed = True


class FakeSSLContext:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def wrap_socket(self, raw, server_hostname):
        assert server_hostname == "pool.example.test"
        return self.endpoint


def _session(incoming=b""):
    endpoint = FakeSocket(incoming)
    raw_sockets = []

    def factory(address, timeout):
        raw = FakeSocket()
        raw_sockets.append(raw)
        return raw

    transport = StratumV1TLSTransport(
        "pool.example.test",
        3333,
        socket_factory=factory,
        ssl_context=FakeSSLContext(endpoint),
    )
    return StratumV1Session("worker.test", transport), endpoint, raw_sockets


def test_session_does_not_connect_automatically_and_requires_approval():
    session, endpoint, raw_sockets = _session()
    assert session.status()["connected"] is False
    with pytest.raises(StratumTransportError, match="TRANSPORT_NOT_CONNECTED"):
        session.subscribe()
    with pytest.raises(StratumTransportError, match="EXPLICIT_USER_APPROVAL_REQUIRED"):
        session.connect(explicit_approval=False, approved_host="pool.example.test")
    assert raw_sockets == []
    assert endpoint.sent == []


def test_session_subscribe_authorize_and_process_correlated_responses():
    incoming = (
        b'{"id":1,"result":[[], "abcd", 4],"error":null}\n'
        b'{"id":2,"result":true,"error":null}\n'
        b'{"id":null,"method":"mining.set_difficulty","params":[2]}\n'
        b'{"id":null,"method":"mining.notify","params":["job1","'
        + b"00" * 32
        + b'","0102","0304",[],"20000000","1d00ffff","65aa0000",true]}\n'
    )
    session, endpoint, _ = _session(incoming)
    session.connect(explicit_approval=True, approved_host="pool.example.test")
    assert session.subscribe() == {"status": "SUBSCRIBE_SENT", "request_id": 1}
    assert b"mining.subscribe" in endpoint.sent[0]
    assert session.process_one()["result"]["status"] == "SUBSCRIBED"
    auth = session.authorize("placeholder-secret")
    assert auth == {"status": "AUTHORIZE_SENT", "request_id": 2}
    assert b"placeholder-secret" in endpoint.sent[1]

    assert session.process_one()["result"]["status"] == "AUTHORIZED"
    assert session.process_one()["result"]["status"] == "DIFFICULTY_UPDATED"
    job = session.process_one()["result"]
    assert job["status"] == "JOB_RECEIVED_UNVERIFIED"
    assert session.status()["share_submission_enabled"] is False
    assert session.status()["live_mining_verified"] is False
    session.close()


def test_session_never_submits_shares_and_does_not_echo_password():
    session, endpoint, _ = _session(b'{"id":1,"result":[[], "abcd", 4],"error":null}\n')
    session.connect(explicit_approval=True, approved_host="pool.example.test")
    session.subscribe()
    assert session.process_one()["result"]["status"] == "SUBSCRIBED"
    result = session.authorize("sensitive-placeholder")
    assert "sensitive-placeholder" not in repr(result)
    assert "sensitive-placeholder" not in repr(session.status())
    with pytest.raises(StratumTransportError, match="LIVE_SHARE_SUBMISSION_NOT_IMPLEMENTED"):
        session.submit_share("job1", "00", "65aa0000", "00000000")
    assert len(endpoint.sent) == 2
    assert all(b"mining.submit" not in message for message in endpoint.sent)
    session.close()
    assert endpoint.closed is True


def test_authorize_is_blocked_until_subscribe_response_is_processed():
    session, endpoint, _ = _session(b'{"id":1,"result":[[], "abcd", 4],"error":null}\n')
    session.connect(explicit_approval=True, approved_host="pool.example.test")
    session.subscribe()

    with pytest.raises(ValueError, match="STRATUM_SUBSCRIBE_REQUIRED"):
        session.authorize("placeholder-secret")

    assert len(endpoint.sent) == 1
    assert b"mining.authorize" not in endpoint.sent[0]
    assert session.status()["protocol"]["authorized"] is False
    session.close()


def test_session_rejects_approved_host_mismatch_before_opening_socket():
    session, endpoint, raw_sockets = _session()
    with pytest.raises(StratumTransportError):
        session.connect(
            explicit_approval=True,
            approved_host="attacker.example.test",
        )
    assert raw_sockets == []
    assert endpoint.sent == []
    assert session.status()["connected"] is False

def test_failed_subscribe_response_never_allows_authorization():
    incoming = b'{"id":1,"result":null,"error":[20,"unauthorized",null]}\n'
    session, endpoint, _ = _session(incoming)
    session.connect(explicit_approval=True, approved_host="pool.example.test")
    session.subscribe()

    result = session.process_one()
    assert result["result"]["status"] == "REJECTED"
    assert session.status()["protocol"]["subscribed"] is False

    with pytest.raises(ValueError, match="STRATUM_SUBSCRIBE_REQUIRED"):
        session.authorize("placeholder-secret")

    assert len(endpoint.sent) == 1
    assert b"mining.authorize" not in endpoint.sent[0]
    assert session.status()["protocol"]["authorized"] is False
    session.close()


def test_denied_authorization_never_marks_session_authorized():
    incoming = (
        b'{"id":1,"result":[[], "abcd", 4],"error":null}\n'
        b'{"id":2,"result":false,"error":null}\n'
    )
    session, endpoint, _ = _session(incoming)
    session.connect(explicit_approval=True, approved_host="pool.example.test")
    session.subscribe()

    assert session.process_one()["result"]["status"] == "SUBSCRIBED"
    assert session.authorize("placeholder-secret")["status"] == "AUTHORIZE_SENT"
    denied = session.process_one()

    assert denied["result"]["status"] == "AUTHORIZATION_DENIED"
    assert session.status()["protocol"]["authorized"] is False
    assert session.status()["share_submission_enabled"] is False
    assert session.status()["live_mining_verified"] is False
    assert len(endpoint.sent) == 2
    assert b"mining.submit" not in b"".join(endpoint.sent)
    session.close()

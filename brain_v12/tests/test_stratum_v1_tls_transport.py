import pytest

from brain_v12.brain.stratum_v1_tls_transport import (
    StratumTransportError,
    StratumV1TLSTransport,
)


class FakeSocket:
    def __init__(self, incoming=b""):
        self.incoming = bytearray(incoming)
        self.sent = []
        self.closed = False
        self.timeout = None

    def settimeout(self, value):
        self.timeout = value

    def sendall(self, payload):
        self.sent.append(payload)

    def recv(self, count):
        if not self.incoming:
            return b""
        data = bytes(self.incoming[:count])
        del self.incoming[:count]
        return data

    def close(self):
        self.closed = True


class FakeSSLContext:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.server_names = []

    def wrap_socket(self, raw, server_hostname):
        self.server_names.append(server_hostname)
        return self.wrapped


def _transport(fake_socket, *, max_line_bytes=4096):
    context = FakeSSLContext(fake_socket)
    calls = []

    def socket_factory(address, timeout):
        calls.append((address, timeout))
        return FakeSocket()

    transport = StratumV1TLSTransport(
        "pool.example.test",
        3333,
        timeout_seconds=2,
        max_line_bytes=max_line_bytes,
        socket_factory=socket_factory,
        ssl_context=context,
    )
    return transport, fake_socket, context, calls


def test_connect_requires_explicit_approval_and_exact_endpoint_confirmation():
    fake = FakeSocket()
    transport, _, _, calls = _transport(fake)
    with pytest.raises(StratumTransportError, match="EXPLICIT_USER_APPROVAL_REQUIRED"):
        transport.connect(explicit_approval=False, approved_host="pool.example.test")
    with pytest.raises(StratumTransportError, match="POOL_ENDPOINT_CONFIRMATION_MISMATCH"):
        transport.connect(explicit_approval=True, approved_host="attacker.example.test")
    assert calls == []
    assert transport.connected is False


def test_tls_transport_connects_only_after_both_gates_and_sends_json_line():
    fake = FakeSocket()
    transport, _, context, calls = _transport(fake)
    transport.connect(explicit_approval=True, approved_host="pool.example.test")
    assert calls == [(("pool.example.test", 3333), 2.0)]
    assert context.server_names == ["pool.example.test"]
    transport.send_message({"id": 1, "method": "mining.subscribe", "params": []})
    assert fake.sent == [b'{"id":1,"method":"mining.subscribe","params":[]}\n']
    assert transport.status()["certificate_validation"] == "SSL_CONTEXT_DEFAULT_VERIFICATION"
    transport.close()
    assert fake.closed is True


def test_receive_parses_json_line_and_keeps_next_buffered_message():
    fake = FakeSocket(b'{"id":1,"result":true,"error":null}\n{"method":"mining.set_difficulty","params":[2]}\n')
    transport, _, _, _ = _transport(fake)
    transport.connect(explicit_approval=True, endpoint_verified=True)
    assert transport.receive_message()["id"] == 1
    second = transport.receive_message()
    assert second["method"] == "mining.set_difficulty"
    transport.close()


def test_transport_rejects_oversized_inbound_and_outbound_lines():
    fake = FakeSocket(b'{"payload":"' + b"x" * 500 + b'"}\n')
    transport, _, _, _ = _transport(fake, max_line_bytes=256)
    transport.connect(explicit_approval=True, endpoint_verified=True)
    with pytest.raises(StratumTransportError, match="INBOUND_LINE_TOO_LARGE"):
        transport.receive_message()
    assert transport.connected is False

    other, _, _, _ = _transport(FakeSocket(), max_line_bytes=256)
    other.connect(explicit_approval=True, endpoint_verified=True)
    with pytest.raises(StratumTransportError, match="OUTBOUND_LINE_TOO_LARGE"):
        other.send_message({"payload": "x" * 400})


def test_transport_rejects_non_object_json_and_closes_on_eof():
    fake = FakeSocket(b'[]\n')
    transport, _, _, _ = _transport(fake)
    transport.connect(explicit_approval=True, endpoint_verified=True)
    with pytest.raises(StratumTransportError, match="STRATUM_MESSAGE_MUST_BE_OBJECT"):
        transport.receive_message()
    assert transport.connected is False

    eof = FakeSocket()
    second, _, _, _ = _transport(eof)
    second.connect(explicit_approval=True, endpoint_verified=True)
    with pytest.raises(StratumTransportError, match="STRATUM_CONNECTION_CLOSED"):
        second.receive_message()
    assert second.connected is False


def test_invalid_endpoint_and_timeout_fail_before_socket_creation():
    with pytest.raises(ValueError, match="INVALID_STRATUM_HOST"):
        StratumV1TLSTransport("pool.example.test/path", 3333, timeout_seconds=2)
    with pytest.raises(ValueError, match="STRATUM_TIMEOUT_OUT_OF_RANGE"):
        StratumV1TLSTransport("pool.example.test", 3333, timeout_seconds=0)

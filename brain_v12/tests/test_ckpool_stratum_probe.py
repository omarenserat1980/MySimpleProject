from __future__ import annotations

import json

from brain_v12.brain.ckpool_stratum_probe import probe_ckpool_stratum


class FakeSocket:
    def __init__(self, response):
        self.response = response
        self.sent = b""
        self.timeout = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def settimeout(self, value): self.timeout = value
    def sendall(self, data): self.sent += data
    def recv(self, size):
        data, self.response = self.response, b""
        return data[:size]


def test_subscribe_only_and_never_claims_mining():
    sock = FakeSocket(b'{"id":1,"result":[[["mining.notify","session"]],"extra",4],"error":null}\n')
    def factory(address, timeout):
        assert address == ("stratum.ckpool.org", 3333)
        assert timeout == 2
        return sock
    result = probe_ckpool_stratum(timeout=2, socket_factory=factory)
    request = json.loads(sock.sent.decode().strip())
    assert request["method"] == "mining.subscribe"
    assert "mining.authorize" not in sock.sent.decode()
    assert "mining.submit" not in sock.sent.decode()
    assert result["subscription_response_present"] is True
    assert result["authorization_sent"] is False
    assert result["share_submission_sent"] is False
    assert result["mining_started"] is False
    assert result["revenue_realized"] is False


def test_timeout_is_fail_closed():
    def factory(*args, **kwargs): raise TimeoutError()
    result = probe_ckpool_stratum(socket_factory=factory)
    assert result["tcp_connected"] is False
    assert result["error_type"] == "TimeoutError"
    assert result["revenue_realized"] is False

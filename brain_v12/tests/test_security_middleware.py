from types import SimpleNamespace
from brain_v12.brain.security_middleware import client_identity, apply_security_headers

class Headers(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, value)

class Response:
    def __init__(self):
        self.headers = Headers()

def test_security_headers_are_applied():
    r = Response()
    apply_security_headers(r)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"

def test_identity_does_not_expose_raw_peer():
    req = SimpleNamespace(headers={}, client=SimpleNamespace(host="192.0.2.1"))
    value = client_identity(req)
    assert "192.0.2.1" not in value
    assert value.startswith("peer:")

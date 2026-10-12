import os

from brain_v12.brain.security_hardening import SecurityHardener


def test_missing_control_key_fails_closed():
    old = os.environ.pop("BRAIN_CONTROL_KEY", None)
    try:
        assert not SecurityHardener().validate_control_key("anything")
    finally:
        if old is not None:
            os.environ["BRAIN_CONTROL_KEY"] = old


def test_rate_limit_blocks_after_threshold():
    h = SecurityHardener()
    h.config = type(h.config)(rate_limit_per_minute=2)
    assert h.allow_rate("client", now=100)
    assert h.allow_rate("client", now=101)
    assert not h.allow_rate("client", now=102)


def test_sensitive_values_are_redacted():
    result = SecurityHardener.redact_mapping({
        "token": "secret",
        "name": "brain",
        "Authorization": "Bearer abcdefghijklmnop",
    })
    assert result["token"] == "[REDACTED]"
    assert result["Authorization"] == "[REDACTED]"
    assert result["name"] == "brain"


def test_security_headers_are_present():
    headers = SecurityHardener.security_headers()
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Cache-Control"] == "no-store"

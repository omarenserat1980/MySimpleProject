from brain_v7.braincore_v2.access_control import AccessController


def test_access_controller_disabled_mode(monkeypatch):
    monkeypatch.setenv("BRAIN_API_AUTH", "false")
    access = AccessController()
    identity = access.authenticate(None)
    assert identity is not None
    assert access.allowed(identity, "code:read")
    assert access.allowed(identity, "code:write")


def test_access_controller_key_and_scope(monkeypatch):
    monkeypatch.setenv("BRAIN_API_AUTH", "true")
    monkeypatch.setenv("BRAIN_API_KEY", "secret-test-key")
    monkeypatch.setenv("BRAIN_API_SCOPES", "brain:read,code:read")
    access = AccessController()
    assert access.authenticate("wrong") is None
    identity = access.authenticate("secret-test-key")
    assert identity is not None
    assert access.allowed(identity, "brain:read")
    assert not access.allowed(identity, "code:write")

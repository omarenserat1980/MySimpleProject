from brain_v7.braincore_v2.remote_ai_gateway import RemoteAIGateway


def test_remote_gateway_is_not_configured_without_secret():
    gateway = RemoteAIGateway(model="test-model")
    assert gateway.configured is False
    result = gateway.ask("hello")
    assert result.status == "NOT_CONFIGURED"


def test_remote_gateway_snapshot_never_exposes_key():
    gateway = RemoteAIGateway(model="test-model")
    snapshot = gateway.snapshot()
    assert "api_key" not in str(snapshot).lower()
    assert snapshot["secret_exposed"] is False

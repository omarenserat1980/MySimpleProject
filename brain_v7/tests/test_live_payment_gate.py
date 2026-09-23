from brain_v7.braincore_v2.live_payment_gate import inspect_live_payment_gate


def test_live_gate_blocks_default_configuration():
    gate = inspect_live_payment_gate({})
    assert not gate.ready
    assert "LIVE_MODE_DISABLED" in gate.blockers
    assert "REAL_PROVIDER_REQUIRED" in gate.blockers


def test_live_gate_requires_all_runtime_checks():
    env = {
        "PAYMENT_LIVE_MODE": "true",
        "PAYMENT_PROVIDER_NAME": "example",
        "PAYMENT_PROVIDER_CONNECTED": "true",
        "PAYMENT_CREDENTIALS_PRESENT": "true",
        "PAYMENT_WEBHOOK_VERIFIED": "true",
        "PAYMENT_PROVIDER_KIND": "real",
    }
    gate = inspect_live_payment_gate(env)
    assert gate.ready
    assert gate.blockers == ()


def test_mock_provider_can_never_be_live():
    env = {
        "PAYMENT_LIVE_MODE": "true",
        "PAYMENT_PROVIDER_NAME": "test",
        "PAYMENT_PROVIDER_CONNECTED": "true",
        "PAYMENT_CREDENTIALS_PRESENT": "true",
        "PAYMENT_WEBHOOK_VERIFIED": "true",
        "PAYMENT_PROVIDER_KIND": "mock",
    }
    gate = inspect_live_payment_gate(env)
    assert not gate.ready
    assert gate.mock_provider
    assert "MOCK_PROVIDER_BLOCKED_IN_LIVE_MODE" in gate.blockers

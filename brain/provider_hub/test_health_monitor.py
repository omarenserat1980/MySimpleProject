from brain.provider_hub.health_monitor import ProviderHealthMonitor


def test_healthy_probe():
    m = ProviderHealthMonitor()
    s = m.check("x", lambda: True, latency_ms=12)
    assert s.healthy is True
    assert m.is_degraded("x") is False


def test_failed_probe_becomes_degraded():
    m = ProviderHealthMonitor()
    s = m.check("x", lambda: False)
    assert s.healthy is False
    assert m.is_degraded("x") is True


def test_exception_is_recorded_as_failure():
    m = ProviderHealthMonitor()

    def broken():
        raise RuntimeError("down")

    s = m.check("x", broken)
    assert s.healthy is False
    assert s.error == "RuntimeError"

from brain.provider_hub.lifecycle import FailoverEngine, ProviderRecord


def test_activation_requires_evidence():
    p = ProviderRecord("x", "payment", 1)
    p.promote("CONFIGURED")
    p.promote("HEALTHY")
    try:
        p.promote("VERIFIED")
    except ValueError as e:
        assert str(e) == "EVIDENCE_REQUIRED_FOR_ACTIVATION"
    else:
        raise AssertionError("provider activated without evidence")


def test_activation_with_evidence():
    p = ProviderRecord("x", "payment", 1)
    p.promote("CONFIGURED")
    p.promote("HEALTHY")
    p.add_evidence("health", {"ok": True})
    p.promote("VERIFIED")
    p.promote("ACTIVE")
    assert p.state == "ACTIVE"


def test_failover_chooses_next_active():
    a = ProviderRecord("a", "runtime", 1, "ACTIVE")
    b = ProviderRecord("b", "runtime", 2, "ACTIVE")
    e = FailoverEngine([a, b])
    assert e.failover("runtime", "a").provider_id == "b"

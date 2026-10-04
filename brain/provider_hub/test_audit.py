from brain.provider_hub.audit import ProviderAuditLog, ProviderEvent


def test_append_and_filter_events():
    log = ProviderAuditLog()
    log.append(ProviderEvent.create("e1", "tap", "HEALTH_FAILED", "timeout"))
    log.append(ProviderEvent.create("e2", "tap", "FAILOVER", "health failure", "health-1"))
    assert len(log.events_for("tap")) == 2
    assert log.events_for("tap")[1].evidence_ref == "health-1"


def test_duplicate_event_rejected():
    log = ProviderAuditLog()
    log.append(ProviderEvent.create("e1", "tap", "HEALTH_FAILED", "timeout"))
    try:
        log.append(ProviderEvent.create("e1", "tap", "FAILOVER", "duplicate"))
    except ValueError as e:
        assert str(e) == "DUPLICATE_EVENT:e1"
    else:
        raise AssertionError("duplicate event accepted")

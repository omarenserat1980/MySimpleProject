from brain.provider_hub.audit import ProviderAuditLog
from brain.provider_hub.health_monitor import ProviderHealthMonitor
from brain.provider_hub.lifecycle import FailoverEngine, ProviderRecord
from brain.provider_hub.failover_service import AuditedFailoverService


def provider(pid, priority, state="ACTIVE"):
    return ProviderRecord(
        provider_id=pid,
        capability="payment",
        state=state,
        priority=priority,
        evidence=[],
    )


def test_selection_is_audited():
    health = ProviderHealthMonitor()
    health.check("primary", lambda: False)
    health.check("backup", lambda: True)
    audit = ProviderAuditLog()
    service = AuditedFailoverService(health, audit, FailoverEngine())
    result = service.choose([provider("primary", 1), provider("backup", 2)], "payment", "evt-1")
    assert result.selected_provider == "backup"
    assert audit.events_for("backup")[0].event_type == "PROVIDER_SELECTED"


def test_exhaustion_is_audited():
    health = ProviderHealthMonitor()
    health.check("primary", lambda: False)
    audit = ProviderAuditLog()
    service = AuditedFailoverService(health, audit, FailoverEngine())
    result = service.choose([provider("primary", 1)], "payment", "evt-2")
    assert result.selected_provider is None
    assert audit.events_for("payment")[0].event_type == "FAILOVER_EXHAUSTED"

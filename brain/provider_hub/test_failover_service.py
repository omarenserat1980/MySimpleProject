from brain.provider_hub.audit import ProviderAuditLog
from brain.provider_hub.health_monitor import ProviderHealthMonitor
from brain.provider_hub.lifecycle import FailoverEngine, ProviderRecord
from brain.provider_hub.failover_service import AuditedFailoverService


def provider(pid, priority, state="ACTIVE"):
    return ProviderRecord(pid, "payment", priority, state, [{"type": "test"}])


def test_selection_is_audited():
    health = ProviderHealthMonitor()
    health.check("primary", lambda: False)
    health.check("backup", lambda: True)
    audit = ProviderAuditLog()
    records = [provider("primary", 1), provider("backup", 2)]
    service = AuditedFailoverService(health, audit, FailoverEngine(records))
    result = service.choose("payment", "evt-1")
    assert result.selected_provider == "backup"
    assert audit.events_for("backup")[0].event_type == "PROVIDER_SELECTED"


def test_exhaustion_is_audited():
    health = ProviderHealthMonitor()
    health.check("primary", lambda: False)
    audit = ProviderAuditLog()
    records = [provider("primary", 1)]
    service = AuditedFailoverService(health, audit, FailoverEngine(records))
    result = service.choose("payment", "evt-2")
    assert result.selected_provider is None
    assert audit.events_for("payment")[0].event_type == "FAILOVER_EXHAUSTED"


def test_failover_selects_healthy_replacement():
    health = ProviderHealthMonitor()
    health.check("primary", lambda: False)
    health.check("backup", lambda: True)
    audit = ProviderAuditLog()
    records = [provider("primary", 1), provider("backup", 2)]
    service = AuditedFailoverService(health, audit, FailoverEngine(records))
    result = service.failover("payment", "primary", "evt-3")
    assert result.selected_provider == "backup"
    assert audit.events_for("backup")[0].event_type == "FAILOVER_SELECTED"

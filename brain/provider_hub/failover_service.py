"""Provider failover service with auditable decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .audit import ProviderAuditLog, ProviderEvent
from .health_monitor import ProviderHealthMonitor
from .lifecycle import FailoverEngine, ProviderRecord


@dataclass(frozen=True)
class FailoverDecision:
    selected_provider: str | None
    reason: str
    evidence_ref: str | None


class AuditedFailoverService:
    def __init__(self, health: ProviderHealthMonitor, audit: ProviderAuditLog, engine: FailoverEngine) -> None:
        self.health = health
        self.audit = audit
        self.engine = engine

    def choose(self, capability: str, event_id: str) -> FailoverDecision:
        candidates = [
            p for p in self.engine.records
            if p.capability == capability and p.state == "ACTIVE"
            and not self.health.is_degraded(p.provider_id)
        ]
        if not candidates:
            self.audit.append(ProviderEvent.create(
                event_id, capability, "FAILOVER_EXHAUSTED", "no healthy active provider"
            ))
            return FailoverDecision(None, "no healthy active provider", None)

        selected = sorted(candidates, key=lambda p: p.priority)[0]
        self.audit.append(ProviderEvent.create(
            event_id, selected.provider_id, "PROVIDER_SELECTED",
            "selected by health and priority policy",
            metadata={"capability": capability},
        ))
        return FailoverDecision(selected.provider_id, "selected by health and priority policy", None)

    def failover(self, capability: str, failed_provider_id: str, event_id: str) -> FailoverDecision:
        candidates = [
            p for p in self.engine.records
            if p.capability == capability and p.provider_id != failed_provider_id
            and p.state == "ACTIVE" and not self.health.is_degraded(p.provider_id)
        ]
        if not candidates:
            self.audit.append(ProviderEvent.create(
                event_id, failed_provider_id, "FAILOVER_EXHAUSTED",
                "no healthy active replacement"
            ))
            return FailoverDecision(None, "no healthy active replacement", None)

        selected = sorted(candidates, key=lambda p: p.priority)[0]
        self.audit.append(ProviderEvent.create(
            event_id, selected.provider_id, "FAILOVER_SELECTED",
            f"replacement for {failed_provider_id}",
        ))
        return FailoverDecision(selected.provider_id, f"replacement for {failed_provider_id}", None)

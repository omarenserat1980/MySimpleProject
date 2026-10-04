"""Provider failover service with auditable decisions."""

from __future__ import annotations

from dataclasses import dataclass

from .audit import ProviderAuditLog, ProviderEvent
from .lifecycle import FailoverEngine, ProviderRecord
from .health_monitor import ProviderHealthMonitor


@dataclass(frozen=True)
class FailoverDecision:
    selected_provider: str | None
    reason: str
    evidence_ref: str | None


class AuditedFailoverService:
    def __init__(
        self,
        health: ProviderHealthMonitor,
        audit: ProviderAuditLog,
        engine: FailoverEngine,
    ) -> None:
        self.health = health
        self.audit = audit
        self.engine = engine

    def choose(
        self,
        providers: list[ProviderRecord],
        capability: str,
        event_id: str,
    ) -> FailoverDecision:
        candidates = [
            p for p in providers
            if p.capability == capability and not self.health.is_degraded(p.provider_id)
        ]
        selected = self.engine.select(candidates)
        if selected is None:
            self.audit.append(
                ProviderEvent.create(
                    event_id, capability, "FAILOVER_EXHAUSTED",
                    "no healthy eligible provider"
                )
            )
            return FailoverDecision(None, "no healthy eligible provider", None)

        self.audit.append(
            ProviderEvent.create(
                event_id,
                selected.provider_id,
                "PROVIDER_SELECTED",
                "selected by health and failover policy",
                metadata={"capability": capability},
            )
        )
        return FailoverDecision(
            selected.provider_id,
            "selected by health and failover policy",
            None,
        )

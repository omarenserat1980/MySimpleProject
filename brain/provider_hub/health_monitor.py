"""Provider health monitor.

Health is operational evidence, not commercial proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass
class HealthSnapshot:
    provider_id: str
    healthy: bool
    checked_at: str
    latency_ms: int | None
    error: str | None = None


class ProviderHealthMonitor:
    def __init__(self) -> None:
        self.snapshots: dict[str, HealthSnapshot] = {}

    def check(self, provider_id: str, probe: Callable[[], bool], latency_ms: int | None = None) -> HealthSnapshot:
        now = datetime.now(timezone.utc).isoformat()
        try:
            healthy = bool(probe())
            error = None
        except Exception as exc:
            healthy = False
            error = type(exc).__name__
        snapshot = HealthSnapshot(provider_id, healthy, now, latency_ms, error)
        self.snapshots[provider_id] = snapshot
        return snapshot

    def is_degraded(self, provider_id: str) -> bool:
        snap = self.snapshots.get(provider_id)
        return bool(snap and not snap.healthy)

    def latest(self, provider_id: str) -> HealthSnapshot | None:
        return self.snapshots.get(provider_id)

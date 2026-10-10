"""Initial freshness classifier for resource heartbeat observations."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HealthState(str, Enum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    INVALID = "INVALID"


@dataclass(frozen=True)
class HealthObservation:
    resource_id: str
    observed_at_epoch: float | None
    now_epoch: float
    ttl_seconds: float = 30.0

    def classify(self) -> HealthState:
        if not self.resource_id.strip() or self.ttl_seconds <= 0:
            return HealthState.INVALID
        if self.observed_at_epoch is None:
            return HealthState.UNKNOWN
        if self.observed_at_epoch < 0 or self.now_epoch < 0 or self.observed_at_epoch > self.now_epoch:
            return HealthState.INVALID
        return HealthState.HEALTHY if self.now_epoch - self.observed_at_epoch <= self.ttl_seconds else HealthState.STALE

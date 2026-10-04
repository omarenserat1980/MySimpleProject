from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class CapabilityStats:
    runs: int = 0
    successes: int = 0
    verified: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0

    @property
    def reliability(self):
        return self.verified / self.runs if self.runs else 0.0

    @property
    def avg_latency_ms(self):
        return self.total_latency_ms / self.runs if self.runs else 0.0

class FabricIntelligence:
    """Bounded learning layer: ranks capabilities from observed evidence only."""
    def __init__(self):
        self.stats: dict[str, CapabilityStats] = {}

    def observe(self, capability: str, *, ok: bool, verified: bool, latency_ms: float = 0.0):
        s = self.stats.setdefault(capability, CapabilityStats())
        s.runs += 1
        s.successes += int(ok)
        s.verified += int(verified)
        s.failures += int(not ok)
        s.total_latency_ms += max(0.0, float(latency_ms))

    def score(self, capability: str, base_priority: int = 100, free: bool = True) -> float:
        s = self.stats.get(capability)
        if not s:
            return (1000.0 if free else 0.0) - base_priority
        exploration = 1.0 / (1.0 + s.runs)
        return (2000.0 if free else 0.0) + 1000.0 * s.reliability + 100.0 * exploration - base_priority - min(s.avg_latency_ms / 1000.0, 100.0)

    def rank(self, capabilities, task: str):
        eligible = [c for c in capabilities if c.enabled and ("*" in c.tasks or task in c.tasks)]
        return sorted(eligible, key=lambda c: (-self.score(c.name, c.priority, c.free), c.name))

    def snapshot(self) -> dict[str, Any]:
        return {"ok": True, "capabilities": {
            k: {"runs": v.runs, "successes": v.successes, "verified": v.verified,
                "failures": v.failures, "reliability": v.reliability,
                "avg_latency_ms": v.avg_latency_ms}
            for k, v in sorted(self.stats.items())
        }}

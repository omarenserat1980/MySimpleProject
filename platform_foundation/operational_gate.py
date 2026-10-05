from __future__ import annotations

from dataclasses import dataclass

from .readiness import ReadinessGate, ReadinessReport
from .runtime import PlatformRuntime


@dataclass(frozen=True)
class OperationalReport:
    ready: bool
    health_passed: bool
    readiness: ReadinessReport | None
    checks: dict[str, bool]


class OperationalGate:
    """Conservative gate for safe transition from foundation to operation."""

    def __init__(
        self,
        runtime: PlatformRuntime,
        readiness: ReadinessGate | None = None,
    ) -> None:
        self.runtime = runtime
        self.readiness_gate = readiness

    def check(self) -> OperationalReport:
        health = self.runtime.health()
        readiness = self.readiness_gate.check() if self.readiness_gate else None
        checks = {
            "runtime_started": self.runtime.started,
            "health": health.passed,
        }
        if readiness is not None:
            checks["foundation_readiness"] = readiness.ready
        return OperationalReport(
            ready=all(checks.values()),
            health_passed=health.passed,
            readiness=readiness,
            checks=checks,
        )


__all__ = ["OperationalGate", "OperationalReport"]

"""Emergency resource circuit breaker.

Protects Brain from continuing to launch new work when system load makes the
runtime effectively unresponsive. It pauses new execution; it does not kill
the operating system or arbitrary processes.
"""
from __future__ import annotations
from dataclasses import dataclass
import os
import time
from typing import Any

@dataclass(frozen=True)
class ResourceLimits:
    cpu_percent: float = 92.0
    memory_percent: float = 92.0
    load_ratio: float = 1.5
    consecutive_breaches: int = 2
    sample_seconds: float = 1.0

class EmergencyResourceGuard:
    def __init__(self, limits: ResourceLimits | None = None):
        self.limits = limits or ResourceLimits()
        self.breaches = 0
        self.emergency = False
        self.last: dict[str, Any] = {}

    def sample(self) -> dict[str, Any]:
        cpu = memory = load = None
        try:
            import psutil
            cpu = float(psutil.cpu_percent(interval=self.limits.sample_seconds))
            memory = float(psutil.virtual_memory().percent)
        except Exception:
            pass
        try:
            load = float(os.getloadavg()[0]) / max(1, os.cpu_count() or 1)
        except (AttributeError, OSError):
            pass
        self.last = {"cpu_percent": cpu, "memory_percent": memory,
                     "load_ratio": load, "ts": time.time()}
        overloaded = (
            (cpu is not None and cpu >= self.limits.cpu_percent)
            or (memory is not None and memory >= self.limits.memory_percent)
            or (load is not None and load >= self.limits.load_ratio)
        )
        self.breaches = self.breaches + 1 if overloaded else 0
        if self.breaches >= self.limits.consecutive_breaches:
            self.emergency = True
        return {**self.last, "overloaded": overloaded,
                "emergency": self.emergency}

    def allow_new_work(self) -> bool:
        return not self.emergency

    def reset_after_recovery(self) -> None:
        self.breaches = 0
        self.emergency = False
        self.last = {}

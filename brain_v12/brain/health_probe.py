"""Brain-owned runtime health scoring and probing."""
from __future__ import annotations

from dataclasses import dataclass
import shutil
import time
from typing import Callable, Any


@dataclass(frozen=True)
class ProbeResult:
    executor_id: str
    available: bool
    latency_ms: int | None = None
    reason: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class HealthState:
    successes: int = 0
    failures: int = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    last_score: float = 0.0

    @property
    def failure_rate(self) -> float:
        total = self.successes + self.failures
        return self.failures / total if total else 0.0


class HealthProbeEngine:
    def __init__(self, cooldown_seconds: float = 30.0):
        self._probes: dict[str, Callable[[], Any]] = {}
        self._results: dict[str, ProbeResult] = {}
        self._states: dict[str, HealthState] = {}
        self.cooldown_seconds = max(0.0, cooldown_seconds)

    def register(self, executor_id: str, probe: Callable[[], Any]) -> None:
        self._probes[executor_id] = probe
        self._states.setdefault(executor_id, HealthState())

    def _score(self, result: ProbeResult, state: HealthState) -> float:
        if not result.available:
            return 0.0
        latency = result.latency_ms
        latency_factor = 1.0 if latency is None else max(0.0, min(1.0, 1000.0 / max(1000.0, latency)))
        reliability = max(0.0, 1.0 - state.failure_rate)
        penalty = min(0.5, state.consecutive_failures * 0.1)
        return round(max(0.0, min(1.0, 0.6 * reliability + 0.3 * latency_factor + 0.1 - penalty)), 4)

    def probe(self, executor_id: str) -> ProbeResult:
        probe = self._probes.get(executor_id)
        if probe is None:
            result = ProbeResult(executor_id, False, reason="NO_PROBE_REGISTERED")
            self._results[executor_id] = result
            return result
        started = time.monotonic()
        try:
            raw = probe()
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if isinstance(raw, dict):
                available = bool(raw.get("available", False))
                reason = raw.get("reason") or raw.get("error")
                details = raw
                latency_ms = raw.get("latency_ms", elapsed_ms)
            else:
                available = bool(raw)
                reason = None if available else "PROBE_RETURNED_FALSE"
                details = {"raw": raw}
                latency_ms = elapsed_ms
            result = ProbeResult(executor_id, available, latency_ms, reason, details)
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            result = ProbeResult(executor_id, False, elapsed_ms, f"PROBE_ERROR:{exc}")
        self._results[executor_id] = result
        state = self._states.setdefault(executor_id, HealthState())
        state.last_score = self._score(result, state)
        if not result.available:
            state.failures += 1
            state.consecutive_failures += 1
            state.cooldown_until = time.time() + self.cooldown_seconds
        else:
            state.successes += 1
            state.consecutive_failures = 0
        return result

    def record_execution(self, executor_id: str, ok: bool) -> None:
        state = self._states.setdefault(executor_id, HealthState())
        if ok:
            state.successes += 1
            state.consecutive_failures = 0
        else:
            state.failures += 1
            state.consecutive_failures += 1
            state.cooldown_until = time.time() + self.cooldown_seconds
        result = self._results.get(executor_id)
        if result:
            state.last_score = self._score(result, state)

    def healthy(self, executor_id: str) -> bool:
        result = self._results.get(executor_id)
        state = self._states.get(executor_id)
        return bool(result and result.available and state and time.time() >= state.cooldown_until)

    def score(self, executor_id: str) -> float:
        return self._states.get(executor_id, HealthState()).last_score

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"executor_id": executor_id, "available": result.available,
             "latency_ms": result.latency_ms, "reason": result.reason,
             "score": self.score(executor_id),
             "failure_rate": self._states.get(executor_id, HealthState()).failure_rate,
             "consecutive_failures": self._states.get(executor_id, HealthState()).consecutive_failures,
             "cooldown_until": self._states.get(executor_id, HealthState()).cooldown_until,
             "details": result.details}
            for executor_id, result in self._results.items()
        ]


def command_probe(command: str) -> Callable[[], dict[str, Any]]:
    def _probe() -> dict[str, Any]:
        path = shutil.which(command)
        return {"available": path is not None, "command": command, "path": path}
    return _probe

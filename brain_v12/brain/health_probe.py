"""Brain-owned runtime probing primitives.

A probe may report availability, but never fabricates successful execution.
"""
from __future__ import annotations

from dataclasses import dataclass
import shutil
from typing import Callable, Any


@dataclass(frozen=True)
class ProbeResult:
    executor_id: str
    available: bool
    latency_ms: int | None = None
    reason: str | None = None
    details: dict[str, Any] | None = None


class HealthProbeEngine:
    def __init__(self):
        self._probes: dict[str, Callable[[], Any]] = {}
        self._results: dict[str, ProbeResult] = {}

    def register(self, executor_id: str, probe: Callable[[], Any]) -> None:
        self._probes[executor_id] = probe

    def probe(self, executor_id: str) -> ProbeResult:
        probe = self._probes.get(executor_id)
        if probe is None:
            result = ProbeResult(executor_id, False, reason="NO_PROBE_REGISTERED")
            self._results[executor_id] = result
            return result
        try:
            raw = probe()
            if isinstance(raw, dict):
                available = bool(raw.get("available", False))
                reason = raw.get("reason") or raw.get("error")
                details = raw
            else:
                available = bool(raw)
                reason = None if available else "PROBE_RETURNED_FALSE"
                details = {"raw": raw}
            result = ProbeResult(executor_id, available, reason=reason, details=details)
        except Exception as exc:
            result = ProbeResult(executor_id, False, reason=f"PROBE_ERROR:{exc}")
        self._results[executor_id] = result
        return result

    def probe_all(self) -> dict[str, ProbeResult]:
        return {executor_id: self.probe(executor_id) for executor_id in self._probes}

    def healthy(self, executor_id: str) -> bool:
        result = self._results.get(executor_id)
        return bool(result and result.available)

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            {"executor_id": r.executor_id, "available": r.available,
             "latency_ms": r.latency_ms, "reason": r.reason, "details": r.details}
            for r in self._results.values()
        ]


def command_probe(command: str) -> Callable[[], dict[str, Any]]:
    def _probe() -> dict[str, Any]:
        path = shutil.which(command)
        return {"available": path is not None, "command": command, "path": path}
    return _probe

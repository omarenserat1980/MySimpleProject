from __future__ import annotations
from dataclasses import dataclass
from time import monotonic
from typing import Any

@dataclass(frozen=True)
class BenchmarkResult:
    capability: str
    ok: bool
    verified: bool
    latency_ms: float
    score: float

def benchmark(fabric, task: str, payload: dict[str, Any], kind: str = "model") -> list[BenchmarkResult]:
    registry = getattr(fabric, kind + "s", {})
    rows = []
    for cap in fabric._candidates(registry, task):
        start = monotonic()
        try:
            result = cap.handler(payload)
            verified = fabric._verify(result)
            ok = isinstance(result, dict) and result.get("ok") is True
        except Exception:
            verified = False
            ok = False
        latency = (monotonic() - start) * 1000
        fabric.intelligence.observe(cap.name, ok=ok, verified=verified, latency_ms=latency)
        score = (1.0 if ok else 0.0) + (1.0 if verified else 0.0) - (latency / 100000.0)
        rows.append(BenchmarkResult(cap.name, ok, verified, round(latency, 3), round(score, 6)))
    return rows

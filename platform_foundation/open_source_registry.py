from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from .open_source_gate import OpenSourceCandidate, OpenSourceGate


class OpenSourceRegistry:
    """Durable registry of evaluated open-source candidates."""

    def __init__(self, path: str | Path = "brain6_artifacts/open_source_registry.json") -> None:
        self.path = Path(path)

    def evaluate_and_record(
        self,
        candidates: list[OpenSourceCandidate],
        *,
        gate: OpenSourceGate | None = None,
    ) -> dict[str, object]:
        gate = gate or OpenSourceGate()
        report = gate.evaluate_all(candidates)
        payload = {
            "policy": "OPEN_SOURCE_FIRST",
            "healthy": report["healthy"],
            "status": report["status"],
            "approved": list(report["approved"]),
            "blocked": list(report["blocked"]),
            "results": [
                {
                    "candidate": result.candidate,
                    "decision": result.decision.value,
                    "reasons": list(result.reasons),
                }
                for result in report["results"]
            ],
            "candidates": [asdict(candidate) for candidate in candidates],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload


__all__ = ["OpenSourceRegistry"]

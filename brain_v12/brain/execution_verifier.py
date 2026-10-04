"""Execution verification and evidence contracts.

A runner result is not success until an explicit verifier accepts it.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable


@dataclass(frozen=True)
class Evidence:
    capability: str
    executor_id: str
    verified: bool
    checks: tuple[str, ...] = ()
    details: dict[str, Any] | None = None


class ExecutionVerifier:
    def __init__(self):
        self._verifiers: dict[str, Callable[[Any], Any]] = {}

    def register(self, capability: str, verifier: Callable[[Any], Any]) -> None:
        self._verifiers[capability] = verifier

    def verify(self, capability: str, executor_id: str, result: Any) -> Evidence:
        verifier = self._verifiers.get(capability)
        if verifier is None:
            return Evidence(capability, executor_id, False, ("NO_VERIFIER_REGISTERED",))
        try:
            raw = verifier(result)
            if isinstance(raw, dict):
                ok = bool(raw.get("verified", False))
                checks = tuple(raw.get("checks", ()))
                details = raw
            else:
                ok = bool(raw)
                checks = ("VERIFIER_ACCEPTED" if ok else "VERIFIER_REJECTED",)
                details = None
            return Evidence(capability, executor_id, ok, checks, details)
        except Exception as exc:
            return Evidence(capability, executor_id, False, ("VERIFIER_ERROR",),
                            {"error": str(exc)})


def evidence_dict(evidence: Evidence) -> dict[str, Any]:
    return asdict(evidence)

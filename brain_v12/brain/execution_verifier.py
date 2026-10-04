"""Artifact-backed execution verification.

Verification may inspect real files and returns auditable evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
import hashlib


@dataclass(frozen=True)
class Evidence:
    capability: str
    executor_id: str
    verified: bool
    checks: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
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
                return Evidence(
                    capability, executor_id, bool(raw.get("verified", False)),
                    tuple(raw.get("checks", ())),
                    tuple(raw.get("artifact_refs", ())),
                    raw,
                )
            return Evidence(capability, executor_id, bool(raw),
                            ("VERIFIER_ACCEPTED" if raw else "VERIFIER_REJECTED",))
        except Exception as exc:
            return Evidence(capability, executor_id, False, ("VERIFIER_ERROR",),
                            details={"error": str(exc)})

    @staticmethod
    def verify_file(path: str, *, min_bytes: int = 1) -> dict[str, Any]:
        p = Path(path)
        checks: list[str] = []
        if not p.is_file():
            return {"verified": False, "checks": ["ARTIFACT_MISSING"],
                    "artifact_refs": (str(p),)}
        size = p.stat().st_size
        if size < min_bytes:
            return {"verified": False, "checks": ["ARTIFACT_EMPTY"],
                    "artifact_refs": (str(p),)}
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        checks.extend(["ARTIFACT_EXISTS", "ARTIFACT_NON_EMPTY", "SHA256_COMPUTED"])
        return {"verified": True, "checks": checks,
                "artifact_refs": (str(p),),
                "sha256": digest, "bytes": size}


def evidence_dict(evidence: Evidence) -> dict[str, Any]:
    return asdict(evidence)

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OpenSourceDecision(str, Enum):
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class OpenSourceCandidate:
    name: str
    region: str
    license: str
    version: str
    self_hosted: bool
    security_reviewed: bool
    reproducible: bool
    evidence: bool


@dataclass(frozen=True)
class OpenSourceGateResult:
    decision: OpenSourceDecision
    candidate: str
    reasons: tuple[str, ...]


class OpenSourceGate:
    """Fail-closed admission gate for third-party open-source components."""

    def evaluate(self, candidate: OpenSourceCandidate) -> OpenSourceGateResult:
        reasons: list[str] = []
        if not candidate.name.strip():
            reasons.append("missing_name")
        if not candidate.region.strip():
            reasons.append("missing_region")
        if not candidate.license.strip():
            reasons.append("missing_license")
        if not candidate.version.strip():
            reasons.append("version_not_pinned")
        if not candidate.self_hosted:
            reasons.append("self_hosting_not_proven")
        if not candidate.security_reviewed:
            reasons.append("security_review_missing")
        if not candidate.reproducible:
            reasons.append("reproducibility_missing")
        if not candidate.evidence:
            reasons.append("evidence_missing")
        decision = (
            OpenSourceDecision.APPROVED
            if not reasons
            else OpenSourceDecision.BLOCKED
        )
        return OpenSourceGateResult(decision, candidate.name, tuple(reasons))


__all__ = [
    "OpenSourceCandidate",
    "OpenSourceDecision",
    "OpenSourceGate",
    "OpenSourceGateResult",
]

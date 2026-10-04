"""Evidence gate for game releases; build status alone is not sale readiness."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class GameReleaseDecision:
    ready: bool
    reasons: tuple[str,...]

def evaluate(*, built: bool, tests_passed: bool, artifact_present: bool, evidence_ref: str|None) -> GameReleaseDecision:
    reasons=[]
    if not built: reasons.append("BUILD_REQUIRED")
    if not tests_passed: reasons.append("TESTS_REQUIRED")
    if not artifact_present: reasons.append("ARTIFACT_REQUIRED")
    if not evidence_ref: reasons.append("EVIDENCE_REQUIRED")
    return GameReleaseDecision(not reasons, tuple(reasons))

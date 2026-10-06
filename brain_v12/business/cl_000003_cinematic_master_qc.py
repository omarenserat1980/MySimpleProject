"""Evidence-gated Cinematic Master QC for CL-000003.

This gate is intentionally separate from technical completion. A valid MP4 is
not automatically a professional film.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

CRITERIA = (
    "story", "screenplay", "directing", "cinematography", "continuity",
    "editing", "sound", "music", "visual_consistency", "originality",
    "provenance_rights", "legal_policy",
)

@dataclass(frozen=True)
class Criterion:
    score: float
    evidence: str

def evaluate(scores: dict[str, Any], *, minimum: float = 80.0,
             required_evidence: bool = True) -> dict[str, Any]:
    failures = []
    normalized = {}
    for name in CRITERIA:
        raw = scores.get(name)
        if not isinstance(raw, dict):
            failures.append(f"{name.upper()}_EVIDENCE_MISSING")
            continue
        try:
            score = float(raw.get("score"))
        except (TypeError, ValueError):
            failures.append(f"{name.upper()}_SCORE_INVALID")
            continue
        evidence = str(raw.get("evidence") or "").strip()
        if score < 0 or score > 100:
            failures.append(f"{name.upper()}_SCORE_OUT_OF_RANGE")
        if required_evidence and not evidence:
            failures.append(f"{name.upper()}_EVIDENCE_MISSING")
        normalized[name] = asdict(Criterion(score=score, evidence=evidence))
        if score < minimum:
            failures.append(f"{name.upper()}_BELOW_MINIMUM")
    average = sum(x["score"] for x in normalized.values()) / len(normalized) if normalized else 0.0
    if len(normalized) != len(CRITERIA):
        failures.append("ALL_CRITERIA_REQUIRED")
    if average < minimum:
        failures.append("MASTER_SCORE_BELOW_MINIMUM")
    passed = not failures
    return {
        "status": "CINEMATIC_PASS" if passed else "DO_NOT_PUBLISH",
        "passed": passed,
        "minimum_score": minimum,
        "average_score": round(average, 2),
        "criteria": normalized,
        "failures": failures,
        "next_action": "RELEASE_GATE" if passed else "DIAGNOSE_REWORK_REPLACE",
    }

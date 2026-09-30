#!/usr/bin/env python3
"""Qur'an-informed reasoning guardrails for BRAIN V12.

This is not a Qur'an interpreter and does not claim that modern science is
encoded in the Qur'an. It stores explicit textual principles as governance
rules for observation, evidence, planning, action, and accountability.

Sources:
- 17:36: do not follow what you have no knowledge of.
- 18:84-85: means/causes (asbab) and following a means.
- 59:18: examine what each self has sent forward for tomorrow.
- 28:77: seek the Hereafter while not forgetting one's worldly share and do good.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass(frozen=True)
class QuranPrinciple:
    key: str
    reference: str
    rule: str
    engine_use: str


PRINCIPLES = (
    QuranPrinciple(
        "knowledge_before_claim",
        "17:36",
        "Do not follow or assert what is not known.",
        "Require evidence status before promoting an observation to a fact.",
    ),
    QuranPrinciple(
        "means_and_causes",
        "18:84-85",
        "Use and follow available means (asbab) toward an objective.",
        "Represent goals as cause/means chains and test the relevant mechanism.",
    ),
    QuranPrinciple(
        "review_before_tomorrow",
        "59:18",
        "Examine what has been put forward for what comes next.",
        "Run retrospective audits before future planning.",
    ),
    QuranPrinciple(
        "worldly_and_ultimate_balance",
        "28:77",
        "Seek the Hereafter while not neglecting one's worldly share; do good.",
        "Keep outcome planning bounded by ethical constraints and real-world needs.",
    ),
)


class QuranReasoningGuard:
    """Deterministic governance layer; theological interpretation remains explicit."""

    def __init__(self) -> None:
        self.principles = {p.key: p for p in PRINCIPLES}

    def require_evidence(self, claim: str, evidence_status: str) -> bool:
        if not claim.strip():
            raise ValueError("claim must be non-empty")
        return evidence_status in {"observed", "verified", "scripture_explicit"}

    def causal_plan(self, goal: str, means: List[str]) -> Dict[str, object]:
        if not goal.strip():
            raise ValueError("goal must be non-empty")
        if not means:
            raise ValueError("at least one means is required")
        return {
            "principle": self.principles["means_and_causes"].reference,
            "goal": goal,
            "means": list(means),
            "sequence": list(means),
            "requires_verification": True,
        }

    def retrospective_check(self, actions: List[str]) -> Dict[str, object]:
        return {
            "principle": self.principles["review_before_tomorrow"].reference,
            "actions_reviewed": list(actions),
            "audit_required": True,
        }

    def governance(self) -> Dict[str, object]:
        return {
            "principles": [asdict(p) for p in PRINCIPLES],
            "rule": "Quranic principles constrain Brain reasoning; they do not manufacture scientific facts.",
        }


def self_test() -> None:
    g = QuranReasoningGuard()
    assert g.require_evidence("observed result", "observed")
    assert not g.require_evidence("unverified claim", "hypothesis")
    plan = g.causal_plan("complete film", ["design", "render", "QC"])
    assert plan["requires_verification"] is True
    assert g.retrospective_check(["render", "QC"])["audit_required"] is True


if __name__ == "__main__":
    self_test()
    print("QURAN_REASONING_GUARD=PASS")

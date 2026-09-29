"""Combined Heart + Nafs internal-state coordinator for Brain Cloud.

This is a software control model inspired by Quranic references. It does not
claim to create a literal human heart, soul, ruh, or spiritual accountability.
Core security, authorization, validation, and human-approval controls remain
authoritative.
"""
from __future__ import annotations

from dataclasses import asdict
from .heart_engine import HeartEngine
from .nafs_policy import NafsPolicy


class BrainInnerState:
    def __init__(self, heart: HeartEngine | None = None, nafs: NafsPolicy | None = None):
        self.heart = heart or HeartEngine()
        self.nafs = nafs or NafsPolicy()

    def evaluate(self, *, action: str, evidence: float = 0.5,
                 ambiguity: float = 0.0, pressure: float = 0.0,
                 social_impact: float = 0.5, benefit: float = 0.5,
                 harm: float = 0.0, temptation: float = 0.0,
                 uncertainty: float = 0.0, reversible: bool = True) -> dict:
        heart_state = self.heart.perceive(
            evidence=evidence,
            ambiguity=ambiguity,
            pressure=pressure,
            social_impact=social_impact,
        )
        heart_review = self.heart.review(
            contradiction=ambiguity,
            new_evidence=evidence,
        )
        nafs = self.nafs.evaluate(
            action,
            benefit=benefit,
            harm=harm,
            temptation=temptation,
            uncertainty=uncertainty,
            reversible=reversible,
        )

        hard_stop = nafs["decision"] in {"REJECT", "DEFER", "REVIEW"}
        heart_review_required = heart_review["action"] == "FORCE_REVIEW"
        decision = "REVIEW" if hard_stop or heart_review_required else "PROCEED_TO_AUTHORIZATION"

        return {
            "decision": decision,
            "heart": {
                "state": asdict(heart_state),
                "review": heart_review,
            },
            "nafs": nafs,
            "authority": "advisory_only",
            "literal_human_inner_state_claim": False,
        }

    def audit(self) -> dict:
        return {
            "heart": self.heart.audit(),
            "nafs": self.nafs.review(),
            "authority": "advisory_only",
            "literal_human_inner_state_claim": False,
        }

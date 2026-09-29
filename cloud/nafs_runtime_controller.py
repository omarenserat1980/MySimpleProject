"""Safe runtime controller for the Quran-informed Nafs layer.

The controller is deliberately advisory: existing authorization, security,
validation, and deployment gates remain authoritative.
"""
from __future__ import annotations
from dataclasses import asdict
from .nafs_gate import NafsGate, NafsGateResult

class NafsRuntimeController:
    def __init__(self, gate: NafsGate | None = None):
        self.gate = gate or NafsGate()

    def preflight(self, action: str, **signals) -> dict:
        result: NafsGateResult = self.gate.check(action=action, **signals)
        return {
            "allowed_by_nafs": result.decision == "ALLOW_WITH_AUDIT",
            "decision": result.decision,
            "state": result.state,
            "reason": result.reason,
            "quran_refs": list(result.quran_refs),
            "human_soul_claim": False,
            "authority": "advisory_only",
        }

    def postflight_review(self) -> dict:
        review = self.gate.engine.self_review()
        review["authority"] = "advisory_only"
        review["human_soul_claim"] = False
        return review

"""Decision governor combining Brain inner state with evidence/ethics checks."""
from __future__ import annotations

from cloud.quranic_brain_principles import governance_check
from cloud.brain_inner_state import BrainInnerState

class BrainGovernor:
    def __init__(self, inner_state: BrainInnerState | None = None):
        self.inner_state = inner_state or BrainInnerState()

    def preflight(self, action: str, payload: dict) -> dict:
        inner = self.inner_state.evaluate(
            action=action,
            evidence=float(payload.get("heart_evidence", 0.5)),
            ambiguity=float(payload.get("heart_ambiguity", payload.get("nafs_uncertainty", 0.0))),
            pressure=float(payload.get("heart_pressure", payload.get("nafs_temptation", 0.0))),
            social_impact=float(payload.get("heart_social_impact", 0.5)),
            benefit=float(payload.get("nafs_benefit", 0.5)),
            harm=float(payload.get("nafs_harm", 0.0)),
            temptation=float(payload.get("nafs_temptation", 0.0)),
            uncertainty=float(payload.get("nafs_uncertainty", 0.0)),
            reversible=bool(payload.get("nafs_reversible", True)),
        )
        governance = governance_check(
            verified=bool(payload.get("evidence_verified", True)),
            entrusted_data=bool(payload.get("entrusted_data", False)),
            fair_basis=bool(payload.get("fair_basis", True)),
            disagreement=bool(payload.get("agent_disagreement", False)),
            consequential=bool(payload.get("consequential", True)),
        )
        review = inner["decision"] == "REVIEW" or not governance["allowed_to_proceed"]
        return {
            "decision": "REVIEW" if review else "PROCEED_TO_AUTHORIZATION",
            "inner_state": inner,
            "governance": governance,
            "authority": "advisory_only",
            "literal_spiritual_claim": False,
        }

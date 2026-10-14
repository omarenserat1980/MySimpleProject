"""Bitcoin North Star: persistent, evidence-first strategic routing for Brain V12.

The compass prioritizes verified progress toward real Bitcoin mining and net profit.
It does not mine, provision resources, spend money, or infer revenue from forecasts.
Persistence is delegated to the existing RunEvidenceStore when supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import hashlib
import json
import time


MISSION = "BITCOIN_NORTH_STAR"
TARGETS = ("REAL_BTC_MINING", "VERIFIED_NET_PROFIT", "BITCOIN_MINING_SOFTWARE")
DEPENDENCIES = ("EXECUTOR_READINESS", "STRATUM_CONNECTIVITY", "ACCEPTED_SHARE_PROOF",
                "PAYOUT_RECONCILIATION", "MINING_ECONOMICS", "SECURITY", "CI_VERIFICATION")
FORBIDDEN_AUTOMATION = ("LIVE_MINING", "SPEND_MONEY", "PROVISION_PAID_RESOURCE",
                        "WITHDRAW_FUNDS", "CHANGE_SECRET", "DEPLOY_PRODUCTION")


@dataclass(frozen=True)
class CompassAssessment:
    task_id: str
    mission: str
    status: str
    alignment_score: float
    direction: str
    reasons: tuple[str, ...]
    next_action: str
    requires_approval: bool
    revenue_claim_allowed: bool = False

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


class BitcoinNorthStar:
    """Deterministic task router with optional append-only evidence persistence."""

    def __init__(self, evidence_store: Any | None = None):
        self.evidence_store = evidence_store

    @staticmethod
    def _tags(task: Mapping[str, Any]) -> set[str]:
        raw = task.get("tags", [])
        if isinstance(raw, str):
            raw = [raw]
        return {str(tag).strip().upper() for tag in raw if str(tag).strip()}

    @staticmethod
    def _bounded_number(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number != number:
            return default
        return max(0.0, min(1.0, number))

    def assess(self, task: Mapping[str, Any]) -> CompassAssessment:
        task_id = str(task.get("task_id", "")).strip()
        if not task_id:
            raise ValueError("TASK_ID_REQUIRED")

        tags = self._tags(task)
        evidence = str(task.get("evidence_status", "MISSING")).strip().upper()
        expected_progress = self._bounded_number(task.get("expected_progress", 0.0))
        cost_ratio = self._bounded_number(task.get("cost_ratio", 0.0))
        risk = str(task.get("risk", "LOW")).strip().upper()
        explicit_target = bool(tags.intersection(TARGETS))
        dependency = bool(tags.intersection(DEPENDENCIES))
        evidence_verified = evidence == "VERIFIED"
        approval_required = bool(task.get("requires_approval", False)) or risk in {"HIGH", "CRITICAL"}
        forbidden = bool(tags.intersection(FORBIDDEN_AUTOMATION))

        reasons: list[str] = []
        if explicit_target:
            alignment = 0.65 + 0.25 * expected_progress
            reasons.append("DIRECT_BITCOIN_MISSION_ALIGNMENT")
        elif dependency:
            alignment = 0.35 + 0.25 * expected_progress
            reasons.append("MISSION_DEPENDENCY")
        else:
            alignment = 0.0
            reasons.append("NO_EXPLICIT_MISSION_LINK")

        if evidence_verified:
            alignment += 0.10
            reasons.append("EVIDENCE_VERIFIED")
        else:
            reasons.append("EVIDENCE_NOT_VERIFIED")

        alignment = round(min(1.0, alignment) * (1.0 - 0.35 * cost_ratio), 4)
        if forbidden:
            status, direction = "BLOCKED", "STOP_AND_REQUIRE_EXPLICIT_APPROVAL"
            reasons.append("CONSEQUENTIAL_ACTION_IS_NEVER_AUTOMATIC")
            next_action = "Prepare a non-executing plan and identify the required authorization."
        elif approval_required:
            status, direction = "APPROVAL_REQUIRED", "HOLD"
            reasons.append("RISK_OR_APPROVAL_GATE")
            next_action = "Gather evidence and request approval before the consequential step."
        elif alignment >= 0.55:
            status, direction = "ON_MISSION", "ADVANCE"
            next_action = str(task.get("next_action", "")).strip() or (
                "Execute the smallest reversible step, then verify its result."
            )
        elif alignment >= 0.30:
            status, direction = "SUPPORTING", "VERIFY_VALUE"
            next_action = "Prove this dependency is blocking Bitcoin progress; otherwise deprioritize it."
        else:
            status, direction = "OFF_COURSE", "DEPRIORITIZE"
            next_action = "Defer this task unless new evidence establishes a material mission dependency."

        result = CompassAssessment(
            task_id=task_id, mission=MISSION, status=status,
            alignment_score=alignment, direction=direction,
            reasons=tuple(reasons), next_action=next_action,
            requires_approval=approval_required or forbidden,
            revenue_claim_allowed=False,
        )
        if self.evidence_store is not None:
            canonical = json.dumps(result.as_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            observed_at = time.time()
            event_id = "north-star-" + hashlib.sha256((task_id + ":" + canonical + ":" + str(observed_at)).encode("utf-8")).hexdigest()
            self.evidence_store.append(
                event_id=event_id,
                task_id=task_id,
                event_type="BITCOIN_NORTH_STAR_ASSESSMENT",
                payload={**result.as_dict(), "observed_at_unix": observed_at},
            )
        return result

    def mission_snapshot(self) -> dict[str, Any]:
        return {
            "mission": MISSION,
            "north_star": "Real, authorized Bitcoin mining and independently verified net profit.",
            "targets": list(TARGETS),
            "dependencies": list(DEPENDENCIES),
            "rules": [
                "Prefer verified progress over activity or code volume.",
                "A forecast, simulation, test pass, or target is not realized BTC revenue.",
                "No paid provisioning, live mining, withdrawal, secret change, or production deployment without explicit approval.",
                "Use the existing evidence store; do not create a competing memory authority.",
                "Reassess and deprioritize work with no evidenced mission link.",
            ],
            "real_mining_verified": False,
            "net_profit_verified": False,
            "status": "MISSION_SET_EVIDENCE_GATES_OPEN",
        }

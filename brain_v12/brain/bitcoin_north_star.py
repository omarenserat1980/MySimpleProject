"""Bitcoin North Star: evidence-first routing with durable blocker lifecycle.

The compass records assessments and blocker transitions in the existing append-only
RunEvidenceStore. Stable blocker IDs prevent repeated assessments from creating new
blockers. The journal is tamper-evident, not an authenticated external evidence source.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping
import hashlib
import json

MISSION = "BITCOIN_NORTH_STAR"
TARGETS = ("REAL_BTC_MINING", "VERIFIED_NET_PROFIT", "BITCOIN_MINING_SOFTWARE")
DEPENDENCIES = (
    "EXECUTOR_READINESS", "STRATUM_CONNECTIVITY", "ACCEPTED_SHARE_PROOF",
    "PAYOUT_RECONCILIATION", "MINING_ECONOMICS", "SECURITY", "CI_VERIFICATION",
)
FORBIDDEN_AUTOMATION = (
    "LIVE_MINING", "SPEND_MONEY", "PROVISION_PAID_RESOURCE",
    "WITHDRAW_FUNDS", "CHANGE_SECRET", "DEPLOY_PRODUCTION",
)
BLOCKER_STATES = ("OPEN", "ACTION_REQUIRED", "VERIFYING", "CLOSED")
_ALLOWED_TRANSITIONS = {
    "OPEN": {"ACTION_REQUIRED"},
    "ACTION_REQUIRED": {"VERIFYING"},
    "VERIFYING": {"CLOSED", "ACTION_REQUIRED"},
    "CLOSED": {"OPEN"},
}


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
    """Deterministic router with idempotent assessments and a durable blocker lifecycle."""

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

    @staticmethod
    def _digest(value: Any) -> str:
        canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _blocker_id(task: Mapping[str, Any]) -> str:
        # blocker_key should be a stable issue key (e.g. MISSING_POOL_SHARE_PROOF).
        # task_id is the safe fallback; component scopes identical keys across owners.
        component = str(task.get("component", task.get("task_id", ""))).strip().upper()
        key = str(task.get("blocker_key", task.get("task_id", ""))).strip().upper()
        if not component or not key:
            raise ValueError("BLOCKER_COMPONENT_AND_STABLE_KEY_REQUIRED")
        return "btc-blocker-" + hashlib.sha256(
            f"{MISSION}:{component}:{key}".encode("utf-8")
        ).hexdigest()[:32]

    def _blocker_events(self, blocker_id: str) -> list[dict[str, Any]]:
        if self.evidence_store is None:
            return []
        return [
            event for event in self.evidence_store.read_all()
            if event.get("event_type") == "BITCOIN_NORTH_STAR_BLOCKER"
            and event.get("payload", {}).get("blocker_id") == blocker_id
        ]

    def blocker_snapshot(self, task: Mapping[str, Any]) -> dict[str, Any]:
        """Return the latest durable state for this stable blocker key."""
        blocker_id = self._blocker_id(task)
        events = self._blocker_events(blocker_id)
        if not events:
            return {
                "blocker_id": blocker_id,
                "state": "OPEN",
                "known": False,
                "next_action": "Record the concrete blocker and its smallest verifiable next step.",
            }
        latest = events[-1]["payload"]
        return {
            "blocker_id": blocker_id,
            "state": latest["state"],
            "known": True,
            "blocker": latest.get("blocker", ""),
            "next_action": latest.get("next_action", ""),
            "evidence_ref": latest.get("evidence_ref"),
            "evidence_source": latest.get("evidence_source"),
        }

    def record_blocker(
        self,
        task: Mapping[str, Any],
        *,
        state: str | None = None,
        blocker: str = "",
        next_action: str = "",
        evidence_ref: str | None = None,
        evidence_source: str | None = None,
        evidence_status: str = "MISSING",
        reopen: bool = False,
    ) -> dict[str, Any]:
        """Append an idempotent, validated blocker transition to the existing journal.

        CLOSED requires a caller-supplied evidence reference/source and VERIFIED label.
        Those fields preserve provenance claims; this local journal cannot authenticate
        a pool, blockchain, or other external provider by itself.
        """
        if self.evidence_store is None:
            raise RuntimeError("EVIDENCE_STORE_REQUIRED_FOR_DURABLE_BLOCKER_STATE")
        blocker_id = self._blocker_id(task)
        events = self._blocker_events(blocker_id)
        current = events[-1]["payload"]["state"] if events else None
        desired = str(state or current or "ACTION_REQUIRED").strip().upper()
        if desired not in BLOCKER_STATES:
            raise ValueError("INVALID_BLOCKER_STATE")
        if desired == "CLOSED":
            if str(evidence_status).strip().upper() != "VERIFIED":
                raise ValueError("CLOSURE_REQUIRES_VERIFIED_EVIDENCE_STATUS")
            if not str(evidence_ref or "").strip() or not str(evidence_source or "").strip():
                raise ValueError("CLOSURE_REQUIRES_EVIDENCE_REFERENCE_AND_SOURCE")
        if current is None:
            if desired not in {"OPEN", "ACTION_REQUIRED"}:
                raise ValueError("BLOCKER_MUST_OPEN_BEFORE_VERIFICATION")
        elif desired != current:
            if desired not in _ALLOWED_TRANSITIONS[current]:
                raise ValueError(f"INVALID_BLOCKER_TRANSITION:{current}->{desired}")
            if current == "CLOSED" and not (reopen and evidence_ref and evidence_source):
                raise ValueError("REOPEN_REQUIRES_EXPLICIT_FLAG_AND_NEW_EVIDENCE")
        elif reopen:
            raise ValueError("REOPEN_REQUIRES_CLOSED_TO_OPEN_TRANSITION")

        payload = {
            "mission": MISSION,
            "blocker_id": blocker_id,
            "component": str(task.get("component", task.get("task_id", ""))).strip(),
            "blocker_key": str(task.get("blocker_key", task.get("task_id", ""))).strip(),
            "state": desired,
            "blocker": str(blocker or task.get("blocker", "")).strip(),
            "next_action": str(next_action or task.get("next_action", "")).strip(),
            "evidence_ref": str(evidence_ref).strip() if evidence_ref else None,
            "evidence_source": str(evidence_source).strip() if evidence_source else None,
            "evidence_status": str(evidence_status).strip().upper(),
        }
        # Same issue + same transition content => same event ID, so re-running the
        # same assessment is idempotent. Changed content is a new event on same issue.
        event_id = "north-star-blocker-" + self._digest(payload)
        saved = self.evidence_store.append(
            event_id=event_id,
            task_id=str(task.get("task_id", blocker_id)).strip(),
            event_type="BITCOIN_NORTH_STAR_BLOCKER",
            payload=payload,
        )
        return {**payload, "duplicate_event": bool(saved.get("duplicate", False))}

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
            payload = result.as_dict()
            event_id = "north-star-assessment-" + self._digest(payload)
            self.evidence_store.append(
                event_id=event_id,
                task_id=task_id,
                event_type="BITCOIN_NORTH_STAR_ASSESSMENT",
                payload=payload,
            )

        # Supplying a stable blocker key activates lifecycle tracking. Reassessment
        # keeps the existing state/action instead of creating a fresh blocker each time.
        if task.get("blocker_key") or task.get("blocker"):
            snapshot = self.blocker_snapshot(task)
            desired_state = task.get("blocker_state") or (
                snapshot["state"] if snapshot["known"] else "ACTION_REQUIRED"
            )
            # A closed blocker stays closed on ordinary reassessment. Do not
            # require the caller to resend old closure evidence or append a new event.
            if not (snapshot["known"] and snapshot["state"] == "CLOSED"
                    and not task.get("blocker_state")):
                self.record_blocker(
                    task,
                    state=str(desired_state),
                    blocker=str(task.get("blocker", "")),
                    next_action=str(task.get("blocker_next_action", next_action)),
                    evidence_ref=task.get("resolution_evidence_ref"),
                    evidence_source=task.get("resolution_evidence_source"),
                    evidence_status=str(task.get("resolution_evidence_status", "MISSING")),
                    reopen=bool(task.get("reopen_blocker", False)),
                )
        return result

    def mission_snapshot(self) -> dict[str, Any]:
        return {
            "mission": MISSION,
            "north_star": "Real, authorized Bitcoin mining and independently verified net profit.",
            "targets": list(TARGETS),
            "dependencies": list(DEPENDENCIES),
            "blocker_states": list(BLOCKER_STATES),
            "rules": [
                "Prefer verified progress over activity or code volume.",
                "A forecast, simulation, test pass, or target is not realized BTC revenue.",
                "No paid provisioning, live mining, withdrawal, secret change, or production deployment without explicit approval.",
                "Use the existing evidence store; do not create a competing memory authority.",
                "Reuse stable blocker IDs and continue the existing action instead of opening duplicate blocker cycles.",
                "A blocker is closed only with a declared verified evidence reference and source; the journal does not authenticate that source.",
                "Reassess and deprioritize work with no evidenced mission link.",
            ],
            "real_mining_verified": False,
            "net_profit_verified": False,
            "status": "MISSION_SET_EVIDENCE_GATES_OPEN",
        }

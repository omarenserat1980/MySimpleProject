"""Fail-closed acceptance gate layered over Brain's existing evidence store.

This module is a verifier, not an orchestrator. It does not execute tasks or
claim remote attestation. It accepts a task only when criterion evidence is
hash-valid, scoped to the requested attempt, at the expected reality level,
and referenced by a separate verification record produced by a different
producer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .evidence_store import EvidenceStore


@dataclass(frozen=True)
class AcceptanceCriterion:
    criterion_id: str
    required_kind: str


@dataclass(frozen=True)
class GoldenGateResult:
    accepted: bool
    status: str
    task_id: str
    mission_id: str | None
    attempt: int | None
    reality_level: str
    evidence_ids: tuple[str, ...]
    criterion_results: tuple[dict[str, Any], ...]
    reasons: tuple[str, ...]


class GoldenAcceptanceGate:
    """Independent acceptance check using existing append-only evidence."""

    def __init__(self, evidence_store: EvidenceStore | None = None) -> None:
        self.evidence = evidence_store or EvidenceStore()

    def evaluate(
        self,
        task_id: str,
        criteria: Iterable[AcceptanceCriterion],
        *,
        mission_id: str | None = None,
        attempt: int | None = None,
        expected_reality: str = "SIMULATED",
    ) -> GoldenGateResult:
        criteria = tuple(criteria)
        if not task_id:
            raise ValueError("TASK_ID_REQUIRED")
        if not criteria:
            raise ValueError("ACCEPTANCE_CRITERIA_REQUIRED")
        if not expected_reality or expected_reality.strip() != expected_reality:
            raise ValueError("EXPECTED_REALITY_INVALID")
        ids = [c.criterion_id for c in criteria]
        if any(not c.criterion_id or not c.required_kind for c in criteria):
            raise ValueError("ACCEPTANCE_CRITERION_INVALID")
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_CRITERION_ID")

        scoped = self.evidence.for_task(
            task_id, mission_id=mission_id, attempt=attempt
        )
        valid_hash: dict[str, dict[str, Any]] = {}
        invalid_hash_ids: set[str] = set()
        for item in scoped:
            check = self.evidence.verify_hash(item["evidence_id"])
            if check.get("ok"):
                valid_hash[item["evidence_id"]] = item
            else:
                invalid_hash_ids.add(item["evidence_id"])

        reasons: list[str] = []
        selected: list[dict[str, Any]] = []
        criterion_results: list[dict[str, Any]] = []
        for criterion in criteria:
            candidates = [
                item for item in valid_hash.values()
                if item.get("kind") == criterion.required_kind
                and str(item.get("kind", "")).lower() not in {"ci", "ci_evidence"}
            ]
            matching_reality = [
                item for item in candidates
                if isinstance(item.get("payload"), dict)
                and item["payload"].get("reality_level") == expected_reality
            ]
            if matching_reality:
                chosen = matching_reality[-1]
                selected.append(chosen)
                criterion_results.append({
                    "criterion_id": criterion.criterion_id,
                    "required_kind": criterion.required_kind,
                    "passed": True,
                    "evidence_id": chosen["evidence_id"],
                })
                continue

            same_kind = [
                item for item in scoped
                if item.get("kind") == criterion.required_kind
            ]
            if any(item["evidence_id"] in invalid_hash_ids for item in same_kind):
                reason = "EVIDENCE_INTEGRITY_FAILURE"
            elif candidates:
                reason = "REALITY_LEVEL_MISMATCH"
            else:
                reason = "ACCEPTANCE_EVIDENCE_MISSING"
            reasons.append(f"{criterion.criterion_id}:{reason}")
            criterion_results.append({
                "criterion_id": criterion.criterion_id,
                "required_kind": criterion.required_kind,
                "passed": False,
                "reason": reason,
            })

        selected_ids = {item["evidence_id"] for item in selected}
        producers = {str(item.get("producer", "")) for item in selected}
        required_criterion_ids = {c.criterion_id for c in criteria}
        independent_records = [
            item for item in valid_hash.values()
            if item.get("kind") == "independent_verification"
            and isinstance(item.get("payload"), dict)
            and item["payload"].get("verified") is True
            and item["payload"].get("reality_level") == expected_reality
            and selected_ids.issubset(set(item["payload"].get("verified_evidence_ids", [])))
            and required_criterion_ids.issubset(set(item["payload"].get("criterion_ids", [])))
            and str(item.get("producer", "")) not in producers
            and bool(item.get("producer"))
        ]
        if not independent_records:
            reasons.append("INDEPENDENT_VERIFICATION_MISSING")

        accepted = not reasons and len(selected) == len(criteria)
        if accepted:
            status = "GOLDEN_LOOP_VERIFIED"
        elif any(reason.endswith("EVIDENCE_INTEGRITY_FAILURE") for reason in reasons):
            status = "EVIDENCE_INTEGRITY_FAILURE"
        elif any(reason.endswith("REALITY_LEVEL_MISMATCH") for reason in reasons):
            status = "REALITY_LEVEL_MISMATCH"
        elif "INDEPENDENT_VERIFICATION_MISSING" in reasons:
            status = "INDEPENDENT_VERIFICATION_MISSING"
        else:
            status = "BLOCKED"

        return GoldenGateResult(
            accepted=accepted,
            status=status,
            task_id=task_id,
            mission_id=mission_id,
            attempt=attempt,
            reality_level=expected_reality,
            evidence_ids=tuple(item["evidence_id"] for item in selected),
            criterion_results=tuple(criterion_results),
            reasons=tuple(reasons),
        )

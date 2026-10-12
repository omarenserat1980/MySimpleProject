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
from .signed_golden_verifier import verify_signed_verification


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

    def __init__(
        self,
        evidence_store: EvidenceStore | None = None,
        *,
        verifier_public_key_b64: str | None = None,
    ) -> None:
        self.evidence = evidence_store or EvidenceStore()
        self.verifier_public_key_b64 = verifier_public_key_b64

    @staticmethod
    def _is_ci_evidence(item: dict[str, Any]) -> bool:
        kind = str(item.get("kind", "")).strip().lower()
        producer = str(item.get("producer", "")).strip().lower()
        return (
            kind in {"ci", "ci_evidence"}
            or producer in {
                "ci", "github-actions", "github-actions-ci",
                "continuous-integration", "ci-runner",
            }
        )

    @staticmethod
    def _references_all(
        payload: dict[str, Any],
        selected_ids: set[str],
        criterion_ids: set[str],
    ) -> bool:
        evidence_refs = payload.get("verified_evidence_ids")
        criterion_refs = payload.get("criterion_ids")
        if not isinstance(evidence_refs, list) or not all(
            isinstance(value, str) for value in evidence_refs
        ):
            return False
        if not isinstance(criterion_refs, list) or not all(
            isinstance(value, str) for value in criterion_refs
        ):
            return False
        return selected_ids.issubset(set(evidence_refs)) and criterion_ids.issubset(set(criterion_refs))

    def evaluate(
        self,
        task_id: str,
        criteria: Iterable[AcceptanceCriterion],
        *,
        mission_id: str | None = None,
        attempt: int | None = None,
        expected_reality: str = "SIMULATED",
    ) -> GoldenGateResult:
        try:
            criteria = tuple(criteria)
        except TypeError as exc:
            raise ValueError("ACCEPTANCE_CRITERIA_INVALID") from exc
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("TASK_ID_REQUIRED")
        if not criteria:
            raise ValueError("ACCEPTANCE_CRITERIA_REQUIRED")
        if (
            not isinstance(expected_reality, str)
            or not expected_reality
            or expected_reality.strip() != expected_reality
        ):
            raise ValueError("EXPECTED_REALITY_INVALID")
        if any(not isinstance(c, AcceptanceCriterion) for c in criteria):
            raise ValueError("ACCEPTANCE_CRITERION_INVALID")
        if any(
            not isinstance(c.criterion_id, str) or not c.criterion_id.strip()
            or not isinstance(c.required_kind, str) or not c.required_kind.strip()
            for c in criteria
        ):
            raise ValueError("ACCEPTANCE_CRITERION_INVALID")
        ids = [c.criterion_id for c in criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_CRITERION_ID")
        # Every acceptance decision must be scoped to exactly one mission
        # attempt, including simulations. Omitting either field must never turn
        # EvidenceStore.for_task() into a cross-attempt query.
        if not isinstance(mission_id, str) or not mission_id.strip():
            error = (
                "REAL_ACCEPTANCE_MISSION_ID_REQUIRED"
                if expected_reality != "SIMULATED"
                else "ACCEPTANCE_MISSION_ID_REQUIRED"
            )
            raise ValueError(error)
        if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
            error = (
                "REAL_ACCEPTANCE_ATTEMPT_REQUIRED"
                if expected_reality != "SIMULATED"
                else "ACCEPTANCE_ATTEMPT_REQUIRED"
            )
            raise ValueError(error)

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
                and not self._is_ci_evidence(item)
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
            and not self._is_ci_evidence(item)
            and isinstance(item.get("payload"), dict)
            and item["payload"].get("verified") is True
            and item["payload"].get("reality_level") == expected_reality
            and self._references_all(item["payload"], selected_ids, required_criterion_ids)
            and str(item.get("producer", "")) not in producers
            and bool(item.get("producer"))
        ]
        independent_verified = bool(independent_records)
        if not independent_records:
            reasons.append("INDEPENDENT_VERIFICATION_MISSING")
        elif expected_reality != "SIMULATED" and len(selected) == len(criteria):
            # Real/remote acceptance requires a cryptographic verifier attestation.
            # A payload label or different producer string is not sufficient.
            signed_ok = False
            signed_errors = []
            expected_scope = {
                "task_id": task_id,
                "mission_id": mission_id,
                "attempt": attempt,
                "reality_level": expected_reality,
                "verified": True,
                "evidence_ids": [item["evidence_id"] for item in selected],
                "criterion_ids": [criterion.criterion_id for criterion in criteria],
            }
            for item in independent_records:
                attestation = item["payload"].get("attestation")
                try:
                    verified_attestation = verify_signed_verification(
                        attestation,
                        public_key_b64=self.verifier_public_key_b64,
                        replay_db_path=self.evidence.path,
                        expected=expected_scope,
                    )
                    if item.get("producer") != verified_attestation["verifier_id"]:
                        raise ValueError("GOLDEN_VERIFIER_PRODUCER_MISMATCH")
                    signed_ok = True
                    break
                except (ValueError, TypeError, KeyError) as exc:
                    signed_errors.append(str(exc))
            if not signed_ok:
                reasons.append("SIGNED_INDEPENDENT_ATTESTATION_REQUIRED")
                reasons.extend("SIGNED_ATTESTATION:" + error for error in signed_errors)

        accepted = not reasons and len(selected) == len(criteria) and independent_verified
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

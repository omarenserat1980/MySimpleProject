"""Fail-closed shared proof gate for Electronic Brain.

This module validates evidence envelopes and evaluates whether each required
proof type has at least one fresh, non-synthetic, revision-matched record.
It validates structure and consistency; it does not independently authenticate
a claimed source or turn local metadata into real-world proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Mapping, Sequence

PASS_STATUSES = frozenset({"PASS", "VERIFIED", "ACCEPTED"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


class ProofGateEngine:
    """Evaluate evidence envelopes against a small declarative gate contract."""

    @staticmethod
    def evaluate(
        *,
        gate_id: str,
        required_proof_types: Sequence[str],
        evidence_records: Sequence[Mapping[str, Any]] | None,
        expected_commit_sha: str | None = None,
        allowed_source_types: Sequence[str] | None = None,
        max_age_seconds: int = 86400,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if not isinstance(gate_id, str) or not gate_id.strip():
            return {"gate_id": gate_id, "status": "UNKNOWN", "reason": "INVALID_GATE_ID", "accepted_evidence_ids": [], "rejected_evidence": []}
        if not required_proof_types or any(not isinstance(x, str) or not x.strip() for x in required_proof_types):
            return {"gate_id": gate_id, "status": "UNKNOWN", "reason": "INVALID_REQUIRED_PROOF_TYPES", "accepted_evidence_ids": [], "rejected_evidence": []}
        if not isinstance(max_age_seconds, int) or max_age_seconds < 0:
            return {"gate_id": gate_id, "status": "UNKNOWN", "reason": "INVALID_FRESHNESS_POLICY", "accepted_evidence_ids": [], "rejected_evidence": []}

        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None or current.utcoffset() is None:
            return {"gate_id": gate_id, "status": "UNKNOWN", "reason": "NOW_MUST_BE_TIMEZONE_AWARE", "accepted_evidence_ids": [], "rejected_evidence": []}
        current = current.astimezone(timezone.utc)
        records = evidence_records if isinstance(evidence_records, Sequence) else []
        accepted: dict[str, str] = {}
        rejected: list[dict[str, str]] = []
        seen_ids: set[str] = set()
        allowed = set(allowed_source_types) if allowed_source_types is not None else None

        for record in records:
            if not isinstance(record, Mapping):
                rejected.append({"evidence_id": "", "reason": "INVALID_RECORD"})
                continue
            evidence_id = record.get("evidence_id")
            proof_type = record.get("proof_type")
            if not isinstance(evidence_id, str) or not evidence_id.strip():
                rejected.append({"evidence_id": "", "reason": "MISSING_EVIDENCE_ID"})
                continue
            if evidence_id in seen_ids:
                rejected.append({"evidence_id": evidence_id, "reason": "DUPLICATE_EVIDENCE_ID"})
                continue
            seen_ids.add(evidence_id)
            if not isinstance(proof_type, str) or not proof_type.strip():
                rejected.append({"evidence_id": evidence_id, "reason": "MISSING_PROOF_TYPE"})
                continue
            if proof_type not in required_proof_types:
                continue
            source_type = record.get("source_type")
            if not isinstance(source_type, str) or not source_type.strip():
                rejected.append({"evidence_id": evidence_id, "reason": "MISSING_SOURCE_TYPE"})
                continue
            if allowed is not None and source_type not in allowed:
                rejected.append({"evidence_id": evidence_id, "reason": "SOURCE_NOT_ALLOWED"})
                continue
            status = record.get("status")
            if status not in PASS_STATUSES:
                rejected.append({"evidence_id": evidence_id, "reason": "EVIDENCE_NOT_VERIFIED"})
                continue
            if record.get("synthetic") is True or str(record.get("environment", "")).lower() in {"test", "simulated", "simulation", "fixture", "mock"}:
                rejected.append({"evidence_id": evidence_id, "reason": "SYNTHETIC_EVIDENCE"})
                continue
            observed = _parse_time(record.get("observed_at"))
            if observed is None:
                rejected.append({"evidence_id": evidence_id, "reason": "INVALID_OBSERVED_AT"})
                continue
            age = (current - observed).total_seconds()
            if age < -60:
                rejected.append({"evidence_id": evidence_id, "reason": "OBSERVATION_FROM_FUTURE"})
                continue
            if age > max_age_seconds:
                rejected.append({"evidence_id": evidence_id, "reason": "STALE_EVIDENCE"})
                continue
            if expected_commit_sha is not None:
                commit_sha = record.get("commit_sha")
                if not isinstance(commit_sha, str) or commit_sha != expected_commit_sha:
                    rejected.append({"evidence_id": evidence_id, "reason": "COMMIT_MISMATCH"})
                    continue
            artifact_sha256 = record.get("artifact_sha256")
            if artifact_sha256 is not None and (not isinstance(artifact_sha256, str) or not SHA256_RE.fullmatch(artifact_sha256)):
                rejected.append({"evidence_id": evidence_id, "reason": "INVALID_ARTIFACT_SHA256"})
                continue
            accepted[proof_type] = evidence_id

        missing = [proof_type for proof_type in required_proof_types if proof_type not in accepted]
        if missing:
            status = "BLOCKED" if not records or any(x["reason"] in {"MISSING_EVIDENCE_ID", "INVALID_RECORD"} for x in rejected) else "FAIL"
            reason = "REQUIRED_EVIDENCE_MISSING" if status == "BLOCKED" else "EVIDENCE_VALIDATION_FAILED"
        else:
            status, reason = "PASS", "ALL_REQUIRED_PROOFS_VALID"

        return {
            "gate_id": gate_id,
            "status": status,
            "reason": reason,
            "required_proof_types": list(required_proof_types),
            "missing_proof_types": missing,
            "accepted_evidence_ids": [accepted[x] for x in required_proof_types if x in accepted],
            "rejected_evidence": rejected,
            "evaluated_at": current.isoformat().replace("+00:00", "Z"),
            "limitations": ["Envelope validation does not independently authenticate the source or prove a physical or financial outcome."],
        }

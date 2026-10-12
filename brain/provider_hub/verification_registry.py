"""Commit-bound verification records for Provider Hub."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib


@dataclass(frozen=True)
class VerificationRecord:
    verification_id: str
    commit_sha: str
    status: str
    test_suite: str
    verified_at: str
    evidence_digest: str


class VerificationRegistry:
    def __init__(self) -> None:
        self._records: dict[str, VerificationRecord] = {}

    def record(
        self,
        verification_id: str,
        commit_sha: str,
        status: str,
        test_suite: str,
        evidence: str,
    ) -> VerificationRecord:
        if verification_id in self._records:
            raise ValueError(f"DUPLICATE_VERIFICATION:{verification_id}")
        if not commit_sha or len(commit_sha) < 7:
            raise ValueError("INVALID_COMMIT_SHA")
        if status not in {"VERIFIED", "NOT_VERIFIED"}:
            raise ValueError("INVALID_VERIFICATION_STATUS")
        digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()
        record = VerificationRecord(
            verification_id=verification_id,
            commit_sha=commit_sha,
            status=status,
            test_suite=test_suite,
            verified_at=datetime.now(timezone.utc).isoformat(),
            evidence_digest=digest,
        )
        self._records[verification_id] = record
        return record

    def latest_for_commit(self, commit_sha: str) -> VerificationRecord | None:
        matches = [r for r in self._records.values() if r.commit_sha == commit_sha]
        if not matches:
            return None
        return max(matches, key=lambda r: r.verified_at)

    def is_currently_verified(self, commit_sha: str, evidence: str) -> bool:
        record = self.latest_for_commit(commit_sha)
        if record is None or record.status != "VERIFIED":
            return False
        digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()
        return digest == record.evidence_digest

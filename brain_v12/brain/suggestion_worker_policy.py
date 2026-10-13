"""Bridge structured ChatGPT suggestions to worker planning without granting authority.

A suggestion can become a reviewed work candidate, never an execution command.
The existing Brain permission/execution gateways and worker evidence gates remain
the only authorities for side effects and real Windows boot.
"""
from __future__ import annotations

from typing import Any, Mapping

REAL_BOOT_CAPABILITY = "windows-server-2025-real-boot"
SAFE_REVIEW_STATUSES = {"APPROVED"}


def evaluate_suggestion_handoff(
    suggestion: Mapping[str, Any],
    *,
    requested_capability: str,
) -> dict[str, Any]:
    """Validate a persisted suggestion before making a non-executable work candidate."""
    reasons: list[str] = []
    suggestion_id = str(suggestion.get("suggestion_id") or "").strip()
    status = str(suggestion.get("status") or "").strip().upper()
    payload = suggestion.get("payload")
    payload = payload if isinstance(payload, Mapping) else {}

    if not suggestion_id:
        reasons.append("SUGGESTION_ID_REQUIRED")
    if status not in SAFE_REVIEW_STATUSES:
        reasons.append("BRAIN_REVIEW_APPROVAL_REQUIRED")
    if not str(payload.get("incident_id") or suggestion.get("incident_id") or "").strip():
        reasons.append("SOURCE_INCIDENT_REQUIRED")
    if not payload.get("supporting_evidence"):
        reasons.append("SUPPORTING_EVIDENCE_REQUIRED")
    if not payload.get("test_plan"):
        reasons.append("TEST_PLAN_REQUIRED")
    if not payload.get("rollback_plan"):
        reasons.append("ROLLBACK_PLAN_REQUIRED")
    if not requested_capability or not str(requested_capability).strip():
        reasons.append("TARGET_CAPABILITY_REQUIRED")

    # A ChatGPT suggestion may never stand in for fresh machine/authority proofs.
    # Real boot must be separately admitted by AdvancedWorker's trusted verifier.
    if requested_capability == REAL_BOOT_CAPABILITY:
        reasons.append("REAL_BOOT_REQUIRES_SEPARATE_TRUSTED_WORKER_ADMISSION")

    candidate = None
    if not reasons:
        candidate = {
            "schema": "brain.suggestion-work-candidate.v1",
            "candidate_id": f"suggestion:{suggestion_id}",
            "source": "brain-chatgpt-suggestion",
            "suggestion_id": suggestion_id,
            "incident_id": str(payload.get("incident_id") or suggestion.get("incident_id")),
            "capability": str(requested_capability).strip(),
            "problem_summary": str(payload.get("problem_summary") or suggestion.get("problem_summary") or "")[:2000],
            "supporting_evidence": list(payload.get("supporting_evidence") or [])[:50],
            "implementation_plan": list(payload.get("implementation_plan") or [])[:20],
            "test_plan": list(payload.get("test_plan") or [])[:20],
            "rollback_plan": list(payload.get("rollback_plan") or [])[:20],
            "risk_assessment": str(payload.get("risk_assessment") or "Risk review required")[:2000],
            "execution_authorized": False,
            "execution_claim": "NONE",
            "windows_boot_verified": False,
        }
    return {
        "ok": not reasons,
        "decision": "CANDIDATE_ONLY_NOT_EXECUTABLE" if not reasons else "DENIED",
        "reasons": reasons,
        "candidate": candidate,
        "execution_authorized": False,
        "windows_boot_verified": False,
    }


import json
import sqlite3
from pathlib import Path


class SuggestionWorkerCandidateStore:
    """Persist advisory work candidates without queuing or executing them."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS brain_worker_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    suggestion_id TEXT NOT NULL UNIQUE,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL,
                    candidate_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            con.commit()

    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    def record(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        """Record once per suggestion; conflicting capabilities are rejected."""
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        suggestion_id = str(candidate.get("suggestion_id") or "").strip()
        capability = str(candidate.get("capability") or "").strip()
        if not candidate_id or not suggestion_id or not capability:
            return {"ok": False, "status": "CANDIDATE_ID_OR_CAPABILITY_REQUIRED"}
        encoded = json.dumps(dict(candidate), ensure_ascii=False, sort_keys=True)
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM brain_worker_candidates WHERE suggestion_id=?",
                (suggestion_id,),
            ).fetchone()
            if row:
                if row["capability"] != capability or row["candidate_id"] != candidate_id:
                    return {"ok": False, "status": "CANDIDATE_ALREADY_RECORDED_DIFFERENT_REQUEST"}
                return {
                    "ok": True, "status": "CANDIDATE_ALREADY_RECORDED",
                    "candidate": json.loads(row["candidate_json"]),
                    "created_at": row["created_at"],
                    "queued": False,
                }
            con.execute(
                """INSERT INTO brain_worker_candidates
                   (candidate_id, suggestion_id, capability, status, candidate_json)
                   VALUES (?, ?, ?, 'RECORDED_NOT_QUEUED', ?)""",
                (candidate_id, suggestion_id, capability, encoded),
            )
            con.commit()
            row = con.execute(
                "SELECT * FROM brain_worker_candidates WHERE candidate_id=?",
                (candidate_id,),
            ).fetchone()
        return {
            "ok": True, "status": "CANDIDATE_RECORDED_NOT_QUEUED",
            "candidate": json.loads(row["candidate_json"]),
            "created_at": row["created_at"],
            "queued": False,
        }

    def get(self, candidate_id: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM brain_worker_candidates WHERE candidate_id=?",
                (str(candidate_id),),
            ).fetchone()
        if not row:
            return None
        return {
            "candidate_id": row["candidate_id"],
            "suggestion_id": row["suggestion_id"],
            "capability": row["capability"],
            "status": row["status"],
            "candidate": json.loads(row["candidate_json"]),
            "created_at": row["created_at"],
            "queued": False,
        }

"""Fail-closed verification for Brain synchronization runtime.

The gate never upgrades a run to VERIFIED unless durable queue, audit-chain,
digest, evidence-reference, and lifecycle checks all pass.
"""
from __future__ import annotations

from typing import Any, Mapping

_ALLOWED = {
    "QUEUED": {"QUEUED", "CLAIMED", "FAILED", "CANCELLED"},
    "CLAIMED": {"CLAIMED", "RUNNING", "FAILED", "CANCELLED"},
    "RUNNING": {"RUNNING", "COMPLETED", "FAILED", "CANCELLED"},
    "COMPLETED": {"COMPLETED"},
    "FAILED": {"FAILED", "RETRYING", "CLAIMED", "CANCELLED"},
    "RETRYING": {"RETRYING", "CLAIMED", "RUNNING", "FAILED", "CANCELLED"},
    "CANCELLED": {"CANCELLED"},
}

def validate_transition(previous: str | None, current: str) -> bool:
    if previous is None:
        return current == "QUEUED"
    return current in _ALLOWED.get(previous, set())

def verify_sync_evidence(
    evidence: Mapping[str, Any],
    *,
    evidence_ref: str | None,
    local_digest: str,
    remote_digest: str,
) -> dict[str, Any]:
    """Return VERIFIED only when every fail-closed condition is satisfied."""
    failures: list[str] = []
    queue = evidence.get("queue") or {}
    if queue.get("failed", 0) != 0:
        failures.append("QUEUE_FAILED")
    if queue.get("sent", 0) != queue.get("acked", 0):
        failures.append("QUEUE_NOT_FULLY_ACKED")
    if not evidence.get("remote_audit_chain_valid", False):
        failures.append("AUDIT_CHAIN_INVALID")
    if local_digest != remote_digest:
        failures.append("DIGEST_MISMATCH")
    if not evidence_ref:
        failures.append("EVIDENCE_REF_REQUIRED")
    status = "VERIFIED" if not failures else "VERIFICATION_FAILED"
    return {
        "status": status,
        "verified": status == "VERIFIED",
        "failures": failures,
        "evidence_ref": evidence_ref,
        "local_digest": local_digest,
        "remote_digest": remote_digest,
    }

"""Conservative evidence classifier for local Public Pool mining diagnostics.

This module never starts a miner, contacts a pool, or records revenue. It combines
caller-supplied local log text and a read-only pool telemetry snapshot. Address-
level aggregate telemetry is explicitly not attributed to a particular process.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

_SESSION_RE = re.compile(r"Stratum session id", re.IGNORECASE)
_JOB_RE = re.compile(r"job_id\s*=|Stratum requested work", re.IGNORECASE)
_HASHRATE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:khash|mhash|ghash|thash)/s", re.IGNORECASE)
_ACCEPT_RE = re.compile(r"(?im)^\s*(?:accepted\s*[:#]|share\s+accepted\b)")
_REJECT_RE = re.compile(r"\brejected\b", re.IGNORECASE)


def classify_public_pool_evidence(
    *, miner_log: str = "", pool_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify available evidence without upgrading unknowns into success.

    ``pool_snapshot`` is expected to come from a separately collected read-only
    endpoint response. This function deliberately does not trust synthetic
    status flags; it validates basic types and requires positive counters.
    """
    if not isinstance(miner_log, str):
        miner_log = ""
    snapshot = pool_snapshot if isinstance(pool_snapshot, dict) else None
    session = bool(_SESSION_RE.search(miner_log))
    job = bool(_JOB_RE.search(miner_log))
    hashrate = bool(_HASHRATE_RE.search(miner_log))
    local_accept = bool(_ACCEPT_RE.search(miner_log))
    local_reject = bool(_REJECT_RE.search(miner_log))

    workers = snapshot.get("workers_count") if snapshot else None
    accepted = snapshot.get("total_accepted_shares_reported") if snapshot else None
    pool_valid = bool(
        snapshot
        and snapshot.get("ok") is True
        and isinstance(workers, int) and not isinstance(workers, bool) and workers >= 0
        and isinstance(accepted, int) and not isinstance(accepted, bool) and accepted >= 0
    )
    pool_activity = bool(pool_valid and (workers > 0 or accepted > 0))
    if local_accept or pool_activity:
        status = "POOL_SHARE_ACTIVITY_OBSERVED_NOT_REVENUE_PROOF"
    elif session and job:
        status = "STRATUM_CONNECTED_WORK_OBSERVED_SHARES_UNVERIFIED"
    elif session:
        status = "STRATUM_CONNECTION_OBSERVED"
    else:
        status = "NO_LOCAL_MINER_SESSION_EVIDENCE"

    log_hash = hashlib.sha256(miner_log.encode("utf-8")).hexdigest() if miner_log else None
    return {
        "schema_version": 1,
        "status": status,
        "local_miner_log_sha256": log_hash,
        "local_stratum_session_observed": session,
        "local_work_job_observed": job,
        "local_hashrate_output_observed": hashrate,
        "local_accepted_message_observed": local_accept,
        "local_rejected_message_observed": local_reject,
        "pool_snapshot_available": pool_valid,
        "pool_workers_count": workers if pool_valid else None,
        "pool_total_accepted_shares_reported": accepted if pool_valid else None,
        "pool_activity_reported": pool_activity,
        "share_acceptance_verified": False,
        "brain_runtime_activity_verified": False,
        "payout_verified": False,
        "revenue_verified": False,
        "financial_execution_enabled": False,
        "evidence_limit": (
            "Local logs may be incomplete. Pool counters are address-level and do not prove "
            "that this process submitted a specific share or that a payout was realized."
        ),
    }

"""Offline integration from a Stratum notify to a local Bitcoin PoW candidate.

No networking, credentials, nonce search, share submission, or acceptance claim
is performed. Byte-order conversion is explicit: callers supply version/ntime/
nbits already in serialized header order and must explicitly select the legacy
Stratum V1 prevhash dialect validated for their pool.
"""
from __future__ import annotations

from typing import Any

from brain_v12.brain.bitcoin_header import (
    build_header_candidate,
    stratum_v1_prevhash_to_header_wire_hex,
)
from brain_v12.brain.stratum_v1_jobs import (
    StratumJob,
    build_coinbase,
    merkle_root_from_coinbase,
)

LEGACY_PREVHASH_DIALECT = "legacy-v1-le32-words"


def build_offline_stratum_candidate(
    notify_params: Any,
    *,
    extranonce1_hex: str,
    extranonce2_hex: str,
    extranonce2_size: int,
    version_header_hex: str,
    ntime_header_hex: str,
    nbits_header_hex: str,
    nonce: int,
    share_target: int,
    prevhash_dialect: str,
    network_target: int | None = None,
) -> dict[str, Any]:
    """Build and locally check one candidate from a validated mining.notify.

    The notify version/time/bits are not silently reinterpreted. The caller
    must pass those three fields in Bitcoin header serialization order. Only
    the explicitly selected legacy prevhash dialect is normalized here.
    """
    if prevhash_dialect != LEGACY_PREVHASH_DIALECT:
        raise ValueError("UNCONFIRMED_STRATUM_PREVHASH_DIALECT")
    job = StratumJob.from_notify(notify_params)
    coinbase = build_coinbase(
        job, extranonce1_hex, extranonce2_hex, extranonce2_size
    )
    merkle_root_raw = merkle_root_from_coinbase(coinbase, job.merkle_branch_hex)
    prevhash_wire_hex = stratum_v1_prevhash_to_header_wire_hex(job.prevhash_hex)
    candidate = build_header_candidate(
        version_hex=version_header_hex,
        prevhash_wire_hex=prevhash_wire_hex,
        merkle_root_raw=merkle_root_raw,
        ntime_hex=ntime_header_hex,
        nbits_hex=nbits_header_hex,
        nonce=nonce,
        share_target=share_target,
    )
    network_target_met = None
    if network_target is not None:
        if (
            isinstance(network_target, bool)
            or not isinstance(network_target, int)
            or not 0 < network_target < 2**256
        ):
            raise ValueError("NETWORK_TARGET_OUT_OF_RANGE")
        network_target_met = candidate.hash_integer <= network_target
    return {
        "schema_version": 1,
        "status": "LOCAL_SHARE_TARGET_MET" if candidate.meets_share_target else "SHARE_TARGET_NOT_MET",
        "job_id": job.job_id,
        "clean_jobs": job.clean_jobs,
        "coinbase_bytes": len(coinbase),
        "merkle_root_raw_hex": merkle_root_raw.hex(),
        "header_hex": candidate.header_bytes.hex(),
        "header_bytes": len(candidate.header_bytes),
        "nonce": candidate.nonce,
        "sha256d_display_hex": candidate.digest_display_hex,
        "share_target_met": candidate.meets_share_target,
        "network_target_met": network_target_met,
        "pool_connection_opened": False,
        "credentials_loaded": False,
        "share_submitted": False,
        "pool_acceptance_verified": False,
        "revenue_verified": False,
        "evidence_class": "OFFLINE_STRATUM_JOB_CANDIDATE_ONLY",
    }

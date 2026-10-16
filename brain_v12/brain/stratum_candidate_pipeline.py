"""Offline Stratum job -> Bitcoin header -> bounded SHA256d candidate pipeline.

This is a deterministic integration layer only. It opens no network sockets,
loads no credentials, starts no background worker, and submits no shares.
Stratum prevhash byte order is pool-specific; callers MUST supply the already
validated 32-byte serialized header representation explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .bitcoin_header import build_header_candidate, compact_nbits_to_target
from .brain_owned_compute_runtime import PowResult, search_nonce
from .stratum_v1_jobs import StratumJob, build_coinbase, merkle_root_from_coinbase


@dataclass(frozen=True)
class OfflineCandidateResult:
    job_id: str
    header_bytes: bytes | None
    merkle_root_raw_hex: str
    hashes_checked: int
    nonce: int | None
    hash_display_hex: str | None
    meets_share_target: bool
    status: str
    pool_contacted: bool = False
    share_submitted: bool = False
    pool_acceptance_verified: bool = False
    revenue_verified: bool = False


def prepare_and_search_job(
    job: StratumJob,
    *,
    extranonce1_hex: str,
    extranonce2_hex: str,
    extranonce2_size: int,
    prevhash_wire_hex: str,
    share_target: int,
    start_nonce: int = 0,
    max_hashes: int = 1_000_000,
) -> OfflineCandidateResult:
    """Build and search one Stratum job under a caller-supplied share target.

    `share_target` is deliberately separate from header `nBits`: Stratum pool
    share difficulty and Bitcoin network target are not interchangeable.
    `prevhash_wire_hex` must be normalized by a pool-specific, vector-tested
    adapter before calling this helper. This function does not guess byte order.
    """
    if not isinstance(job, StratumJob):
        raise ValueError("VALIDATED_STRATUM_JOB_REQUIRED")
    coinbase = build_coinbase(job, extranonce1_hex, extranonce2_hex, extranonce2_size)
    merkle_root = merkle_root_from_coinbase(coinbase, job.merkle_branch_hex)
    initial = build_header_candidate(
        version_hex=job.version_hex,
        prevhash_wire_hex=prevhash_wire_hex,
        merkle_root_raw=merkle_root,
        ntime_hex=job.ntime_hex,
        nbits_hex=job.nbits_hex,
        nonce=start_nonce,
        share_target=share_target,
    )
    pow_result: PowResult = search_nonce(
        initial.header_bytes, share_target,
        start_nonce=start_nonce, max_hashes=max_hashes,
    )
    if not pow_result.found or pow_result.nonce is None:
        return OfflineCandidateResult(
            job_id=job.job_id,
            header_bytes=None,
            merkle_root_raw_hex=merkle_root.hex(),
            hashes_checked=pow_result.hashes_checked,
            nonce=None,
            hash_display_hex=None,
            meets_share_target=False,
            status=pow_result.status,
        )

    candidate = build_header_candidate(
        version_hex=job.version_hex,
        prevhash_wire_hex=prevhash_wire_hex,
        merkle_root_raw=merkle_root,
        ntime_hex=job.ntime_hex,
        nbits_hex=job.nbits_hex,
        nonce=pow_result.nonce,
        share_target=share_target,
    )
    if not candidate.meets_share_target or candidate.digest_display_hex != pow_result.hash_hex:
        raise AssertionError("POW_RESULT_REVALIDATION_FAILED")
    return OfflineCandidateResult(
        job_id=job.job_id,
        header_bytes=candidate.header_bytes,
        merkle_root_raw_hex=merkle_root.hex(),
        hashes_checked=pow_result.hashes_checked,
        nonce=candidate.nonce,
        hash_display_hex=candidate.digest_display_hex,
        meets_share_target=candidate.meets_share_target,
        status="NONCE_FOUND_UNSUBMITTED",
    )


def validate_job_network_target(job: StratumJob) -> dict[str, Any]:
    """Decode the network nBits target for diagnostics only, not share difficulty."""
    target = compact_nbits_to_target(job.nbits_hex)
    return {
        "job_id": job.job_id,
        "network_target_hex": f"{target:064x}",
        "share_target_supplied_separately": True,
        "pool_acceptance_verified": False,
        "real_mining_verified": False,
    }

"""Brain-owned native SHA256d proof-of-work primitive.

This module performs real double-SHA256 nonce search over an 80-byte Bitcoin
header. It is NOT a complete pool miner: it does not implement Stratum, create
coinbase/merkle data, authorize a pool session, or submit shares. It never starts
work automatically. A separate attested compute host and reviewed pool adapter
are required before this can be used for live mining.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import platform
from typing import Any

GITHUB_ACTION_MARKERS = ("GITHUB_ACTIONS", "CI")


@dataclass(frozen=True)
class PowResult:
    found: bool
    nonce: int | None
    hashes_checked: int
    hash_hex: str | None
    status: str


def double_sha256(data: bytes) -> bytes:
    """Return Bitcoin-style SHA256d digest bytes."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def validate_header(header: bytes) -> None:
    if not isinstance(header, bytes) or len(header) != 80:
        raise ValueError("BITCOIN_HEADER_MUST_BE_80_BYTES")


def validate_target(target: int) -> None:
    if isinstance(target, bool) or not isinstance(target, int) or not 0 < target < 2**256:
        raise ValueError("TARGET_OUT_OF_RANGE")


def partition_nonce_range(
    start_nonce: int,
    end_nonce_exclusive: int,
    partitions: int,
) -> tuple[tuple[int, int], ...]:
    """Split a nonce interval into deterministic, disjoint half-open ranges.

    `end_nonce_exclusive` may be 2**32 to include the maximum uint32 nonce.
    Empty ranges are omitted when partitions outnumber available nonces.
    This is scheduling metadata only; it does not start or parallelize work.
    """
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if (isinstance(end_nonce_exclusive, bool) or not isinstance(end_nonce_exclusive, int)
            or not start_nonce < end_nonce_exclusive <= 2**32):
        raise ValueError("END_NONCE_EXCLUSIVE_OUT_OF_RANGE")
    if isinstance(partitions, bool) or not isinstance(partitions, int) or not 1 <= partitions <= 1_000_000:
        raise ValueError("PARTITION_COUNT_OUT_OF_RANGE")

    total = end_nonce_exclusive - start_nonce
    count = min(total, partitions)
    base, remainder = divmod(total, count)
    ranges: list[tuple[int, int]] = []
    cursor = start_nonce
    for index in range(count):
        width = base + (1 if index < remainder else 0)
        end = cursor + width
        ranges.append((cursor, end))
        cursor = end
    if cursor != end_nonce_exclusive:
        raise AssertionError("NONCE_PARTITION_COVERAGE_FAILURE")
    return tuple(ranges)


def search_nonce(
    header: bytes,
    target: int,
    *,
    start_nonce: int = 0,
    max_hashes: int = 1_000_000,
) -> PowResult:
    """Search actual SHA256d hashes; header's final 4 bytes are nonce LE.

    This bounded primitive is intentionally separate from pool networking and
    never claims a share was accepted. A found nonce must be submitted through a
    trusted, algorithm-compatible pool adapter and independently verified.
    """
    validate_header(header)
    validate_target(target)
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if isinstance(max_hashes, bool) or not isinstance(max_hashes, int) or not 1 <= max_hashes <= 10_000_000:
        raise ValueError("MAX_HASHES_OUT_OF_RANGE")

    prefix = header[:76]
    checked = 0
    nonce = start_nonce
    while checked < max_hashes and nonce <= 0xFFFFFFFF:
        candidate = prefix + nonce.to_bytes(4, "little")
        digest = double_sha256(candidate)
        checked += 1
        # Bitcoin proof-of-work interprets the digest as a little-endian integer.
        if int.from_bytes(digest, "little") <= target:
            return PowResult(True, nonce, checked, digest[::-1].hex(), "NONCE_FOUND_UNSUBMITTED")
        nonce += 1
    return PowResult(False, None, checked, None, "NONCE_NOT_FOUND_WITHIN_BOUND")


def build_nonce_search_checkpoint(
    header: bytes,
    target: int,
    job_id: str,
    start_nonce: int,
    result: PowResult,
) -> dict[str, Any]:
    """Create a job/header/target-bound checkpoint after a no-hit bounded search.

    This is a plain data contract, not an authenticated token. Callers must
    authenticate persisted checkpoints before trusting them across processes.
    A found nonce is not resumable and must be handled as an unsubmitted candidate.
    """
    validate_header(header)
    validate_target(target)
    if not isinstance(job_id, str) or not job_id or len(job_id) > 256:
        raise ValueError("INVALID_CHECKPOINT_JOB_ID")
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if not isinstance(result, PowResult) or result.found or result.nonce is not None or result.status != "NONCE_NOT_FOUND_WITHIN_BOUND":
        raise ValueError("CHECKPOINT_REQUIRES_EXHAUSTED_NO_HIT_RESULT")
    if isinstance(result.hashes_checked, bool) or not isinstance(result.hashes_checked, int) or result.hashes_checked < 1:
        raise ValueError("INVALID_CHECKPOINT_HASH_COUNT")
    next_nonce = start_nonce + result.hashes_checked
    if next_nonce > 0xFFFFFFFF:
        raise ValueError("NONCE_SPACE_EXHAUSTED")
    return {
        "schema_version": 1,
        "job_id": job_id,
        "header_sha256": hashlib.sha256(header).hexdigest(),
        "target_hex": f"{target:064x}",
        "start_nonce": start_nonce,
        "next_nonce": next_nonce,
        "hashes_checked": result.hashes_checked,
        "status": "BOUNDED_NO_HIT_CHECKPOINT",
        "authenticated": False,
    }


def validate_nonce_search_checkpoint(
    checkpoint: Any,
    header: bytes,
    target: int,
    job_id: str,
) -> int:
    """Validate checkpoint bindings and return the next nonce, failing closed.

    This validates consistency only; it does not authenticate who created the
    checkpoint. Production persistence must verify a signature/MAC separately.
    """
    validate_header(header)
    validate_target(target)
    if not isinstance(job_id, str) or not job_id or len(job_id) > 256:
        raise ValueError("INVALID_CHECKPOINT_JOB_ID")
    if not isinstance(checkpoint, dict) or checkpoint.get("schema_version") != 1:
        raise ValueError("INVALID_CHECKPOINT_SCHEMA")
    if checkpoint.get("status") != "BOUNDED_NO_HIT_CHECKPOINT" or checkpoint.get("authenticated") is not False:
        raise ValueError("INVALID_CHECKPOINT_STATUS")
    if checkpoint.get("job_id") != job_id:
        raise ValueError("CHECKPOINT_JOB_MISMATCH")
    if checkpoint.get("header_sha256") != hashlib.sha256(header).hexdigest():
        raise ValueError("CHECKPOINT_HEADER_MISMATCH")
    if checkpoint.get("target_hex") != f"{target:064x}":
        raise ValueError("CHECKPOINT_TARGET_MISMATCH")
    next_nonce = checkpoint.get("next_nonce")
    if isinstance(next_nonce, bool) or not isinstance(next_nonce, int) or not 0 <= next_nonce <= 0xFFFFFFFF:
        raise ValueError("INVALID_CHECKPOINT_NEXT_NONCE")
    checked = checkpoint.get("hashes_checked")
    if isinstance(checked, bool) or not isinstance(checked, int) or checked < 1:
        raise ValueError("INVALID_CHECKPOINT_HASH_COUNT")
    start_nonce = checkpoint.get("start_nonce")
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("INVALID_CHECKPOINT_START_NONCE")
    if start_nonce + checked != next_nonce:
        raise ValueError("CHECKPOINT_RANGE_ARITHMETIC_MISMATCH")
    return next_nonce


def is_android_or_termux_runtime() -> bool:
    """Detect Android/Termux so a phone cannot be mistaken for Brain cloud compute."""
    if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA") or os.environ.get("TERMUX_VERSION"):
        return True
    prefix = os.environ.get("PREFIX", "").replace("\\", "/").lower()
    return "/data/data/com.termux/" in prefix or prefix.endswith("/com.termux/files/usr")


def execution_host_gate(
    *,
    attested_brain_compute_host: bool,
    explicit_approval: bool,
    pool_adapter_ready: bool,
    resource_budget_verified: bool,
    physical_gateway_only: bool = True,
) -> dict[str, Any]:
    """Fail-closed gate. This function reports policy; it does not start work."""
    blockers: list[str] = []
    if not attested_brain_compute_host:
        blockers.append("BRAIN_COMPUTE_HOST_NOT_ATTESTED")
    if not explicit_approval:
        blockers.append("EXPLICIT_EXECUTION_APPROVAL_REQUIRED")
    if not pool_adapter_ready:
        blockers.append("STRATUM_POOL_ADAPTER_NOT_IMPLEMENTED")
    if not resource_budget_verified:
        blockers.append("ZERO_COST_COMPUTE_RESOURCE_NOT_VERIFIED")
    if not physical_gateway_only:
        blockers.append("PHYSICAL_GATEWAY_COMPUTATION_FORBIDDEN")
    if platform.system().lower() != "linux":
        blockers.append("SUPPORTED_LINUX_RUNTIME_REQUIRED")
    if is_android_or_termux_runtime():
        blockers.append("PHYSICAL_ANDROID_GATEWAY_COMPUTATION_FORBIDDEN")
    if any(os.environ.get(marker) for marker in GITHUB_ACTION_MARKERS):
        blockers.append("CI_AND_GITHUB_ACTIONS_MINING_FORBIDDEN")
    return {
        "status": "READY_FOR_REVIEW" if not blockers else "BLOCKED",
        "execution_allowed": False,
        "execution_started": False,
        "physical_devices_role": "CONNECTIVITY_OBSERVATION_ONLY",
        "native_pow_primitive": "IMPLEMENTED_SHA256D",
        "stratum_pool_adapter": "NOT_IMPLEMENTED",
        "real_mining_verified": False,
        "revenue_verified": False,
        "blockers": blockers,
    }

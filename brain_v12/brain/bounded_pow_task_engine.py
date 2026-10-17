"""Cooperative, bounded offline proof-of-work task runner.

This is an in-process task primitive for deterministic tests and local simulation.
It opens no sockets, loads no credentials, starts no background threads, and never
submits a candidate. Cancellation is cooperative between bounded hash batches.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable

from .brain_owned_compute_runtime import PowResult, search_nonce, validate_header, validate_target

MAX_TASK_HASHES = 10_000_000
MAX_BATCH_HASHES = 10_000


@dataclass(frozen=True)
class PowTaskResult:
    status: str
    start_nonce: int
    next_nonce: int
    hashes_checked: int
    nonce: int | None = None
    hash_hex: str | None = None
    pool_contacted: bool = False
    share_submitted: bool = False
    pool_acceptance_verified: bool = False
    revenue_verified: bool = False


def run_bounded_pow_task(
    header: bytes,
    target: int,
    *,
    start_nonce: int = 0,
    max_total_hashes: int = 100_000,
    batch_hashes: int = 1_000,
    timeout_seconds: float = 30.0,
    cancel_requested: Callable[[], bool] | None = None,
) -> PowTaskResult:
    """Run bounded SHA256d work with cooperative cancellation and a wall timeout.

    The total hash budget is capped independently of the per-batch size. The
    timeout/cancel checks occur before each batch, so cancellation latency is
    bounded by one batch, not by the entire task. A found nonce is only an
    unsubmitted candidate; this function has no network or pool integration.
    """
    validate_header(header)
    validate_target(target)
    if isinstance(start_nonce, bool) or not isinstance(start_nonce, int) or not 0 <= start_nonce <= 0xFFFFFFFF:
        raise ValueError("START_NONCE_OUT_OF_RANGE")
    if isinstance(max_total_hashes, bool) or not isinstance(max_total_hashes, int) or not 1 <= max_total_hashes <= MAX_TASK_HASHES:
        raise ValueError("MAX_TOTAL_HASHES_OUT_OF_RANGE")
    if isinstance(batch_hashes, bool) or not isinstance(batch_hashes, int) or not 1 <= batch_hashes <= MAX_BATCH_HASHES:
        raise ValueError("BATCH_HASHES_OUT_OF_RANGE")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 3600:
        raise ValueError("TIMEOUT_SECONDS_OUT_OF_RANGE")
    if cancel_requested is not None and not callable(cancel_requested):
        raise ValueError("CANCEL_CHECK_MUST_BE_CALLABLE")

    deadline = time.monotonic() + float(timeout_seconds)
    next_nonce = start_nonce
    total_checked = 0

    while total_checked < max_total_hashes and next_nonce <= 0xFFFFFFFF:
        if cancel_requested is not None and cancel_requested():
            return PowTaskResult("CANCELLED", start_nonce, next_nonce, total_checked)
        if time.monotonic() >= deadline:
            return PowTaskResult("TIMED_OUT", start_nonce, next_nonce, total_checked)

        batch_limit = min(batch_hashes, max_total_hashes - total_checked)
        result: PowResult = search_nonce(
            header, target, start_nonce=next_nonce, max_hashes=batch_limit
        )
        total_checked += result.hashes_checked

        if result.found:
            return PowTaskResult(
                result.status, start_nonce, result.nonce + 1,
                total_checked, result.nonce, result.hash_hex
            )

        next_nonce += result.hashes_checked
        if next_nonce > 0xFFFFFFFF:
            return PowTaskResult("NONCE_SPACE_EXHAUSTED", start_nonce, next_nonce, total_checked)

    return PowTaskResult("HASH_BUDGET_EXHAUSTED", start_nonce, next_nonce, total_checked)

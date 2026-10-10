"""Initial evidence verification and bounded recovery planning skeleton."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    expected_sha256: str
    actual_sha256: str | None
    reason: str


def verify_file_sha256(path: str | Path, expected_sha256: str) -> VerificationResult:
    """Verify a file digest; absence or malformed expectation fails closed."""
    expected = expected_sha256.strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        return VerificationResult(VerificationStatus.REJECTED, expected, None, "EXPECTED_SHA256_INVALID")
    try:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return VerificationResult(VerificationStatus.REJECTED, expected, None, "ARTIFACT_UNREADABLE")
    if digest != expected:
        return VerificationResult(VerificationStatus.REJECTED, expected, digest, "SHA256_MISMATCH")
    return VerificationResult(VerificationStatus.VERIFIED, expected, digest, "SHA256_MATCH")


@dataclass(frozen=True)
class RecoveryDecision:
    retry_allowed: bool
    next_attempt: int
    max_attempts: int
    reason: str


def plan_recovery(attempt: int, max_attempts: int, *, retryable: bool) -> RecoveryDecision:
    """Plan a bounded retry only; never perform the retry."""
    if attempt < 1 or max_attempts < 1 or attempt > max_attempts:
        return RecoveryDecision(False, attempt, max_attempts, "ATTEMPT_RANGE_INVALID")
    if not retryable:
        return RecoveryDecision(False, attempt, max_attempts, "FAILURE_NOT_RETRYABLE")
    if attempt >= max_attempts:
        return RecoveryDecision(False, attempt, max_attempts, "RETRY_LIMIT_REACHED")
    return RecoveryDecision(True, attempt + 1, max_attempts, "BOUNDED_RETRY_PLANNED_NOT_EXECUTED")

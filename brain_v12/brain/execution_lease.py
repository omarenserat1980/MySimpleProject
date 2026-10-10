"""Initial lease contract for future distributed Brain workers.

This module only creates and evaluates lease records in memory. It does not
claim tasks, contact agents, or persist state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LeaseStatus(str, Enum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class ExecutionLease:
    lease_id: str
    task_id: str
    executor_id: str
    fencing_token: int
    issued_at_epoch: float
    expires_at_epoch: float

    def validate(self, now_epoch: float) -> LeaseStatus:
        if (
            not self.lease_id.strip()
            or not self.task_id.strip()
            or not self.executor_id.strip()
            or self.fencing_token < 1
            or self.issued_at_epoch < 0
            or self.expires_at_epoch <= self.issued_at_epoch
            or now_epoch < self.issued_at_epoch
        ):
            return LeaseStatus.INVALID
        if now_epoch >= self.expires_at_epoch:
            return LeaseStatus.EXPIRED
        return LeaseStatus.VALID


def issue_lease(
    task_id: str,
    executor_id: str,
    fencing_token: int,
    issued_at_epoch: float,
    ttl_seconds: float,
) -> ExecutionLease:
    """Build a lease value; caller must provide a unique, monotonic fencing token."""
    if not task_id.strip() or not executor_id.strip():
        raise ValueError("TASK_AND_EXECUTOR_REQUIRED")
    if fencing_token < 1:
        raise ValueError("FENCING_TOKEN_INVALID")
    if issued_at_epoch < 0 or ttl_seconds <= 0:
        raise ValueError("LEASE_TIME_INVALID")
    return ExecutionLease(
        lease_id=f"lease-{task_id}-{fencing_token}",
        task_id=task_id,
        executor_id=executor_id,
        fencing_token=fencing_token,
        issued_at_epoch=issued_at_epoch,
        expires_at_epoch=issued_at_epoch + ttl_seconds,
    )

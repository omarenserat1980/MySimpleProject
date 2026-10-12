"""Authority state model for Brain.

These states are evidence-derived. Configuration alone can never advance the
system to autonomous authority.
"""
from __future__ import annotations

from enum import StrEnum


class AuthorityState(StrEnum):
    INTERNAL_RUNTIME_CODE_PRESENT = "INTERNAL_RUNTIME_CODE_PRESENT"
    INTERNAL_RUNNER_PREFLIGHT_VERIFIED = "INTERNAL_RUNNER_PREFLIGHT_VERIFIED"
    INTERNAL_RUNNER_ONLINE = "INTERNAL_RUNNER_ONLINE"
    TASK_EXECUTED = "TASK_EXECUTED"
    TASK_VERIFIED = "TASK_VERIFIED"
    AUTONOMOUS_WITHIN_AUTHORITY = "AUTONOMOUS_WITHIN_AUTHORITY"


def derive_authority_state(
    *,
    runtime_code: bool = False,
    preflight_verified: bool = False,
    runner_online: bool = False,
    task_executed: bool = False,
    task_verified: bool = False,
    autonomy_certified: bool = False,
) -> str:
    if autonomy_certified and task_verified and task_executed and runner_online:
        return AuthorityState.AUTONOMOUS_WITHIN_AUTHORITY.value
    if task_verified:
        return AuthorityState.TASK_VERIFIED.value
    if task_executed:
        return AuthorityState.TASK_EXECUTED.value
    if runner_online:
        return AuthorityState.INTERNAL_RUNNER_ONLINE.value
    if preflight_verified:
        return AuthorityState.INTERNAL_RUNNER_PREFLIGHT_VERIFIED.value
    if runtime_code:
        return AuthorityState.INTERNAL_RUNTIME_CODE_PRESENT.value
    return "NOT_READY"

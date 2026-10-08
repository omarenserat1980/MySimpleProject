"""Brain Authority Model.

Authority is explicit and monotonic: capability never implies authority.
Models may propose; policy authorizes; executors act; verifiers decide evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import hashlib
import hmac
import os
from typing import Iterable


class AuthorityLevel(IntEnum):
    OBSERVE = 10
    PROPOSE = 20
    EXECUTE_LOW = 30
    EXECUTE_MEDIUM = 40
    EXECUTE_HIGH = 50
    EXECUTE_CRITICAL = 60
    ROOT = 100


@dataclass(frozen=True)
class AuthorityDecision:
    subject: str
    action: str
    level: AuthorityLevel
    authorized: bool
    reason: str
    policy_version: str = "authority-policy-v1"

    def as_dict(self) -> dict:
        return {
            "subject": self.subject,
            "action": self.action,
            "level": self.level.name,
            "authorized": self.authorized,
            "reason": self.reason,
            "policy_version": self.policy_version,
        }


class BrainAuthorityPolicy:
    """Fail-closed authority boundary for consequential execution."""

    MODEL_SUBJECTS = {"model", "chatgpt", "reasoner"}
    EXECUTOR_SUBJECTS = {"executor", "cloud-executor", "windows-real-boot-qemu"}

    def decide(
        self,
        *,
        subject: str,
        action: str,
        risk: str,
        capability: bool,
        human_approval_token: str | None = None,
        root_authority_token: str | None = None,
    ) -> AuthorityDecision:
        risk = str(risk).upper()
        if risk not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            return AuthorityDecision(subject, action, AuthorityLevel.OBSERVE, False, "INVALID_RISK")

        root_secret = os.environ.get("BRAIN_ROOT_AUTHORITY_TOKEN", "")
        if root_authority_token and root_secret and hmac.compare_digest(root_authority_token, root_secret):
            return AuthorityDecision(subject, action, AuthorityLevel.ROOT, True, "ROOT_AUTHORITY_TOKEN_VERIFIED")

        if subject in self.MODEL_SUBJECTS:
            return AuthorityDecision(subject, action, AuthorityLevel.PROPOSE, False, "MODEL_MAY_PROPOSE_NOT_EXECUTE")

        if subject in self.EXECUTOR_SUBJECTS and not capability:
            return AuthorityDecision(subject, action, AuthorityLevel.OBSERVE, False, "CAPABILITY_REQUIRED")

        if risk == "LOW":
            return AuthorityDecision(subject, action, AuthorityLevel.EXECUTE_LOW, capability, "LOW_RISK_CAPABILITY")
        if risk == "MEDIUM":
            return AuthorityDecision(subject, action, AuthorityLevel.EXECUTE_MEDIUM, capability, "MEDIUM_RISK_CAPABILITY")
        approval_secret = os.environ.get("BRAIN_HUMAN_APPROVAL_TOKEN", "")
        approval_ok = bool(human_approval_token and approval_secret and hmac.compare_digest(human_approval_token, approval_secret))
        if risk == "HIGH":
            return AuthorityDecision(subject, action, AuthorityLevel.EXECUTE_HIGH, capability and approval_ok, "HIGH_RISK_REQUIRES_VERIFIED_HUMAN_APPROVAL")
        return AuthorityDecision(subject, action, AuthorityLevel.EXECUTE_CRITICAL, capability and approval_ok, "CRITICAL_REQUIRES_VERIFIED_HUMAN_APPROVAL")


def require_authorized(decision: AuthorityDecision) -> None:
    if not decision.authorized:
        raise PermissionError(f"AUTHORITY_DENIED:{decision.reason}")

"""Trusted approval verification contract.

Production implementations must verify consent evidence using a trusted identity
provider and a protected key or signed provider response. This package deliberately
ships with a deny-all verifier; caller-supplied booleans are not identity proof.
"""
from __future__ import annotations

from typing import Protocol

from .family_governance import FamilyApproval


class FamilyApprovalVerifier(Protocol):
    def verify(self, *, approval: FamilyApproval, action: str,
               task_fingerprint: str) -> bool:
        """Return True only after cryptographically/externally verifying scoped consent."""
        ...


class DenyAllFamilyApprovalVerifier:
    """Safe default until a trusted identity/consent integration is configured."""

    def verify(self, *, approval: FamilyApproval, action: str,
               task_fingerprint: str) -> bool:
        return False

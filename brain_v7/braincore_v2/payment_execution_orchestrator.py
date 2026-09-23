"""Cognitive payment execution orchestrator.

The brain reasons through a real payment as a gated transaction, rather than
pretending that a plan or a request is a transfer. Credentials stay in the
provider adapter, outside the brain core.

Lifecycle:
CREATED -> VALIDATING_FUNDS -> DESTINATION_VERIFIED -> RISK_CHECK ->
APPROVAL_REQUIRED -> SUBMITTED -> PENDING -> CONFIRMED/FAILED/REVERSED

A real transfer can occur only when the provider adapter is configured, the
destination is verified, risk/compliance/limits checks pass, the user supplies
explicit authorization for this exact request, and the provider returns a
submission reference.

This module does not store PINs, passwords, API keys, card numbers, or secrets.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Protocol
import hashlib
import time
from .payment_state_machine import transition
from .governance import append_audit, evaluate_authorized_action

class PaymentProvider(Protocol):
    def submit_transfer(self, *, amount_jod: float, destination_ref: str,
                        reason: str, idempotency_key: str) -> dict[str, Any]:
        ...

class AuthorizationVerifier(Protocol):
    def verify(self, *, intent: "TransferIntent", authorization: str) -> bool:
        """Verify an authorization proof produced by the trusted user-facing layer."""
        ...

@dataclass(frozen=True)
class TransferIntent:
    amount_jod: float
    destination_ref: str
    reason: str
    request_id: str

@dataclass(frozen=True)
class CognitiveDecision:
    status: str
    state: str
    action: str
    requires_user_authorization: bool
    provider_ready: bool
    checks: dict[str, str]
    explanation: str

def request_id(amount_jod: float, destination_ref: str, reason: str) -> str:
    raw = f"{round(float(amount_jod), 2)}|{destination_ref.strip()}|{reason.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def reason_about_transfer(*, amount_jod: float, destination_ref: str, reason: str,
                          funds_available_jod: float | None,
                          destination_verified: bool, risk_clear: bool,
                          compliance_clear: bool,
                          daily_remaining_jod: float | None,
                          provider_ready: bool) -> CognitiveDecision:
    checks = {
        "positive_amount": "PASS" if amount_jod > 0 else "FAIL",
        "funds": ("PASS" if funds_available_jod is not None and funds_available_jod >= amount_jod
                  else "FAIL_OR_UNKNOWN"),
        "destination": "PASS" if destination_verified else "FAIL",
        "risk": "PASS" if risk_clear else "FAIL",
        "compliance": "PASS" if compliance_clear else "FAIL",
        "daily_limit": ("PASS" if daily_remaining_jod is not None and daily_remaining_jod >= amount_jod
                        else "FAIL_OR_UNKNOWN"),
        "provider": "PASS" if provider_ready else "FAIL",
    }
    hard_fail = any(v == "FAIL" for v in checks.values())
    unknown = any(v == "FAIL_OR_UNKNOWN" for v in checks.values())
    if hard_fail:
        return CognitiveDecision("BLOCKED", "CREATED", "DO_NOT_SUBMIT", True,
                                 provider_ready, checks,
                                 "A required safety or compliance condition failed.")
    if unknown:
        return CognitiveDecision("NEEDS_DATA", "CREATED", "REQUEST_MISSING_DATA", True,
                                 provider_ready, checks,
                                 "The brain cannot truthfully claim that the transfer is ready.")
    if not provider_ready:
        return CognitiveDecision("NOT_READY", "CREATED", "CONFIGURE_PROVIDER", True,
                                 False, checks,
                                 "No authenticated payment provider is available.")
    return CognitiveDecision("READY_FOR_AUTHORIZATION", "APPROVAL_REQUIRED",
                             "REQUEST_USER_AUTHORIZATION", True, True, checks,
                             "All pre-transfer checks passed; explicit authorization is still required.")

class PaymentExecutionOrchestrator:
    """Stateful, idempotent execution gate for one transfer intent."""
    def __init__(self, provider: PaymentProvider | None = None,
                 authorization_verifier: AuthorizationVerifier | None = None) -> None:
        self.provider = provider
        self.authorization_verifier = authorization_verifier
        self.state = "CREATED"
        self.last_result: dict[str, Any] | None = None

    def readiness(self, *, amount_jod: float, destination_ref: str, reason: str,
                  funds_available_jod: float | None, destination_verified: bool,
                  risk_clear: bool, compliance_clear: bool,
                  daily_remaining_jod: float | None) -> dict[str, Any]:
        decision = reason_about_transfer(
            amount_jod=amount_jod, destination_ref=destination_ref, reason=reason,
            funds_available_jod=funds_available_jod,
            destination_verified=destination_verified, risk_clear=risk_clear,
            compliance_clear=compliance_clear, daily_remaining_jod=daily_remaining_jod,
            provider_ready=self.provider is not None,
        )
        if decision.status == "READY_FOR_AUTHORIZATION":
            self.state = "APPROVAL_REQUIRED"
        result = asdict(decision)
        result["request_id"] = request_id(amount_jod, destination_ref, reason)
        append_audit("payment_readiness", result)
        return result

    def execute_authorized(self, *, intent: TransferIntent,
                           authorization: str) -> dict[str, Any]:
        """Execute only an explicit authorization for the exact transfer."""
        if self.provider is None:
            raise RuntimeError("PAYMENT_PROVIDER_NOT_CONFIGURED")
        if not authorization or not authorization.strip():
            raise PermissionError("EXPLICIT_AUTHORIZATION_REQUIRED")
        if self.authorization_verifier is None:
            raise PermissionError("AUTHORIZATION_VERIFIER_NOT_CONFIGURED")
        if not self.authorization_verifier.verify(intent=intent, authorization=authorization):
            raise PermissionError("AUTHORIZATION_INVALID")
        policy = evaluate_authorized_action("transfer_money", user_authorized=True)
        if not policy.allowed:
            raise PermissionError("GOVERNANCE_BLOCKED")
        if self.state != "APPROVAL_REQUIRED":
            raise RuntimeError(f"TRANSFER_NOT_READY:{self.state}")

        self.state = transition(self.state, "SUBMITTED")
        try:
            result = self.provider.submit_transfer(
                amount_jod=round(intent.amount_jod, 2),
                destination_ref=intent.destination_ref,
                reason=intent.reason,
                idempotency_key=intent.request_id,
            )
        except Exception as exc:
            self.state = "FAILED"
            self.last_result = {"status": "FAILED", "state": self.state,
                                "error": type(exc).__name__,
                                "request_id": intent.request_id}
            append_audit("payment_failed", self.last_result)
            return self.last_result

        # Normalize both dict-style production adapters and TransferResult objects.
        if hasattr(result, "provider_reference"):
            provider_reference = str(result.provider_reference or "").strip()
            provider_status = str(result.status or "").upper()
            provider_amount = getattr(result, "amount_jod", None)
        else:
            provider_reference = str(result.get("provider_reference", "")).strip()
            provider_status = str(result.get("status", "")).upper()
            provider_amount = result.get("amount_jod")
        if provider_amount is not None and round(float(provider_amount), 2) != round(intent.amount_jod, 2):
            self.state = "FAILED"
            self.last_result = {
                "status": "FAILED", "state": self.state,
                "error": "PROVIDER_AMOUNT_MISMATCH",
                "request_id": intent.request_id,
            }
            append_audit("payment_failed", self.last_result)
            return self.last_result
        if not provider_reference:
            self.state = "FAILED"
            self.last_result = {"status": "FAILED", "state": self.state,
                                "error": "PROVIDER_REFERENCE_MISSING",
                                "request_id": intent.request_id}
            append_audit("payment_failed", self.last_result)
            return self.last_result

        self.state = transition(self.state, "PENDING")
        if provider_status in {"CONFIRMED", "COMPLETED"}:
            self.state = transition(self.state, "CONFIRMED")
            status = "TRANSFER_CONFIRMED"
        else:
            status = "TRANSFER_SUBMITTED"

        self.last_result = {
            "status": status, "state": self.state, "request_id": intent.request_id,
            "provider_reference": provider_reference,
            "amount_jod": round(intent.amount_jod, 2),
            "destination_ref": intent.destination_ref,
            "submitted_at": time.time(),
        }
        append_audit("payment_submitted", self.last_result)
        return self.last_result

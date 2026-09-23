"""Tests for the cognitive payment execution gate."""
from brain_v7.braincore_v2.payment_execution_orchestrator import (
    PaymentExecutionOrchestrator, TransferIntent, reason_about_transfer,
)

class FakeProvider:
    def __init__(self, status="PENDING"):
        self.status = status
        self.calls = []
    def submit_transfer(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": self.status, "provider_reference": "PROV-123"}

def ready_args():
    return dict(
        amount_jod=100.0, destination_ref="wallet:verified",
        reason="authorized payout", funds_available_jod=150.0,
        destination_verified=True, risk_clear=True, compliance_clear=True,
        daily_remaining_jod=100.0,
    )

def test_reasoning_never_claims_transfer_without_provider():
    decision = reason_about_transfer(**ready_args(), provider_ready=False)
    assert decision.status == "NOT_READY"
    assert decision.action == "CONFIGURE_PROVIDER"

def test_ready_requires_explicit_authorization():
    provider = FakeProvider()
    brain = PaymentExecutionOrchestrator(provider)
    readiness = brain.readiness(**ready_args())
    assert readiness["status"] == "READY_FOR_AUTHORIZATION"
    intent = TransferIntent(100.0, "wallet:verified", "authorized payout", readiness["request_id"])
    try:
        brain.execute_authorized(intent=intent, authorization="")
    except PermissionError as exc:
        assert str(exc) == "EXPLICIT_AUTHORIZATION_REQUIRED"
    else:
        raise AssertionError("authorization must be required")

def test_real_provider_submission_is_truthful_and_idempotency_key_is_bound():
    provider = FakeProvider()
    brain = PaymentExecutionOrchestrator(provider)
    readiness = brain.readiness(**ready_args())
    intent = TransferIntent(100.0, "wallet:verified", "authorized payout", readiness["request_id"])
    result = brain.execute_authorized(intent=intent, authorization="USER_APPROVED_EXACT_REQUEST")
    assert result["status"] == "TRANSFER_SUBMITTED"
    assert result["provider_reference"] == "PROV-123"
    assert provider.calls[0]["idempotency_key"] == readiness["request_id"]

def test_provider_confirmation_allows_confirmed_state():
    provider = FakeProvider(status="CONFIRMED")
    brain = PaymentExecutionOrchestrator(provider)
    readiness = brain.readiness(**ready_args())
    intent = TransferIntent(100.0, "wallet:verified", "authorized payout", readiness["request_id"])
    result = brain.execute_authorized(intent=intent, authorization="USER_APPROVED_EXACT_REQUEST")
    assert result["status"] == "TRANSFER_CONFIRMED"
    assert result["state"] == "CONFIRMED"

def test_failed_precondition_blocks_readiness():
    provider = FakeProvider()
    brain = PaymentExecutionOrchestrator(provider)
    args = ready_args()
    args["destination_verified"] = False
    result = brain.readiness(**args)
    assert result["status"] == "BLOCKED"
    assert result["action"] == "DO_NOT_SUBMIT"
    assert not provider.calls

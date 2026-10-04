from brain.provider_hub.verification_registry import VerificationRegistry


def test_verification_is_bound_to_commit_and_evidence():
    registry = VerificationRegistry()
    registry.record("v1", "abcdef1234567", "VERIFIED", "pytest-provider-hub", "PASS 42")
    assert registry.is_currently_verified("abcdef1234567", "PASS 42")
    assert not registry.is_currently_verified("abcdef1234567", "PASS 41")
    assert not registry.is_currently_verified("different123", "PASS 42")


def test_unverified_status_cannot_claim_current_verification():
    registry = VerificationRegistry()
    registry.record("v2", "abcdef7654321", "NOT_VERIFIED", "pytest-provider-hub", "FAIL 1")
    assert not registry.is_currently_verified("abcdef7654321", "FAIL 1")


def test_duplicate_verification_is_rejected():
    registry = VerificationRegistry()
    registry.record("v3", "abcdef1234567", "VERIFIED", "pytest", "PASS")
    try:
        registry.record("v3", "abcdef1234567", "VERIFIED", "pytest", "PASS")
        assert False
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_VERIFICATION:v3"

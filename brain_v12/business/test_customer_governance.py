from customer_governance import Consent, CustomerOperation, CustomerProfile, build_customer_policy

def test_marketing_requires_consent():
    p = CustomerProfile("c1", "Example")
    result = CustomerOperation("c1", "SEND_MESSAGE", "EMAIL", "MARKETING").authorize(p)
    assert result["status"] == "REQUIRES_CONSENT"

def test_service_message_with_consent_still_needs_external_gate():
    p = CustomerProfile("c1", "Example", ["EMAIL"])
    p.add_consent(Consent("SERVICE", True, "customer_portal"))
    result = CustomerOperation("c1", "SEND_MESSAGE", "EMAIL", "SERVICE").authorize(p)
    assert result["status"] == "REQUIRES_AUTHORIZATION"

def test_financial_action_requires_evidence():
    p = CustomerProfile("c1", "Example")
    result = CustomerOperation("c1", "PAYMENT").authorize(p)
    assert result["status"] == "REQUIRES_AUTHORIZATION"
    assert result["reason"] == "EVIDENCE_REQUIRED"

def test_policy_is_fail_closed():
    policy = build_customer_policy()
    assert policy["external_execution"] is False
    assert policy["financial_execution"] is False
    assert policy["marketing_requires_consent"] is True

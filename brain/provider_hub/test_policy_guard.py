from brain.provider_hub.policy_guard import CommercialPolicy, CommercialPolicyGuard


def test_financial_action_is_blocked_by_default():
    decision = CommercialPolicyGuard().authorize(
        financial_action=True, evidence_present=True, contained=False
    )
    assert decision.allowed is False
    assert decision.reason == "FINANCIAL_AUTHORIZATION_REQUIRED"


def test_contained_order_is_blocked_even_when_authorized():
    guard = CommercialPolicyGuard(CommercialPolicy(financial_action_authorized=True))
    decision = guard.authorize(
        financial_action=True, evidence_present=True, contained=True
    )
    assert decision.allowed is False
    assert decision.reason == "ORDER_CONTAINED"


def test_authorized_nonfinancial_operation_can_proceed():
    decision = CommercialPolicyGuard().authorize(
        financial_action=False, evidence_present=False, contained=False
    )
    assert decision.allowed is True
    assert decision.reason == "AUTHORIZED"


def test_authorized_financial_operation_still_needs_evidence():
    guard = CommercialPolicyGuard(CommercialPolicy(financial_action_authorized=True))
    decision = guard.authorize(
        financial_action=True, evidence_present=False, contained=False
    )
    assert decision.allowed is False
    assert decision.reason == "FINANCIAL_EVIDENCE_REQUIRED"

from brain.provider_hub.action_gate import CommercialActionGate
from brain.provider_hub.containment import CommercialContainmentGate
from brain.provider_hub.policy_guard import CommercialPolicyGuard, CommercialPolicy


def gate(authorized=False):
    return CommercialActionGate(
        CommercialPolicyGuard(
            CommercialPolicy(financial_action_authorized=authorized)
        ),
        CommercialContainmentGate(),
    )


def test_financial_action_requires_authorization():
    result = gate().check(order_id="o1", financial_action=True, evidence_present=True)
    assert result.allowed is False
    assert result.reason == "FINANCIAL_AUTHORIZATION_REQUIRED"


def test_authorized_financial_action_requires_evidence():
    result = gate(True).check(order_id="o1", financial_action=True, evidence_present=False)
    assert result.allowed is False
    assert result.reason == "FINANCIAL_EVIDENCE_REQUIRED"


def test_contained_order_is_blocked():
    containment = CommercialContainmentGate()
    containment.contain("i1", "o1", "TEST")
    action = CommercialActionGate(
        CommercialPolicyGuard(CommercialPolicy(financial_action_authorized=True)),
        containment,
    )
    result = action.check(order_id="o1", financial_action=True, evidence_present=True)
    assert result.allowed is False
    assert result.reason == "ORDER_CONTAINED"


def test_safe_nonfinancial_action_is_allowed():
    result = gate().check(order_id="o1", financial_action=False, evidence_present=False)
    assert result.allowed is True
    assert result.reason == "AUTHORIZED"

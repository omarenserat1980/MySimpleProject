from cloud.standing_authorization import (
    ApprovalStatus, CustomerConsent, Risk, StandingAuthorization,
    customer_gate, execution_gate, operator_gate,
)


def test_disabled_authorization_requires_operator_approval():
    status = operator_gate(
        authorization=StandingAuthorization(enabled=False),
        risk=Risk.ROUTINE,
    )
    assert status == ApprovalStatus.REQUIRED


def test_routine_action_within_limit_is_covered():
    status = operator_gate(
        authorization=StandingAuthorization(enabled=True, monetary_limit=100),
        risk=Risk.ROUTINE,
        amount=50,
        currency="JOD",
    )
    assert status == ApprovalStatus.NOT_REQUIRED


def test_high_impact_always_requires_operator():
    status = operator_gate(
        authorization=StandingAuthorization(enabled=True, monetary_limit=10000),
        risk=Risk.HIGH_IMPACT,
        amount=10,
        currency="JOD",
    )
    assert status == ApprovalStatus.REQUIRED


def test_customer_consent_must_match_scope_and_version():
    consent = CustomerConsent(
        approved=True, scope_ref="QUOTE-1", approved_version="v2",
        approved_amount=50, approved_currency="JOD", evidence_ref="approval-1",
    )
    assert customer_gate(
        required=True, consent=consent, scope_ref="QUOTE-1", version="v2",
        amount=50, currency="JOD",
    ) == ApprovalStatus.APPROVED
    assert customer_gate(
        required=True, consent=consent, scope_ref="QUOTE-1", version="v3",
        amount=50, currency="JOD",
    ) == ApprovalStatus.REQUIRED


def test_execution_requires_both_layers():
    auth = StandingAuthorization(enabled=True, monetary_limit=100)
    op = operator_gate(authorization=auth, risk=Risk.ROUTINE, amount=50, currency="JOD")
    consent = CustomerConsent(
        approved=True, scope_ref="QUOTE-1", approved_version="v1",
        approved_amount=50, approved_currency="JOD", evidence_ref="e1",
    )
    cu = customer_gate(required=True, consent=consent, scope_ref="QUOTE-1", version="v1", amount=50, currency="JOD")
    assert execution_gate(operator_status=op, customer_status=cu)

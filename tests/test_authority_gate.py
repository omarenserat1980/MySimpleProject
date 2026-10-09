import pytest
from platform_foundation.authority_gate import AuthorityGate, AuthorityLevel, AuthorityPolicy
from platform_foundation.permissions import ActionRisk


def test_unknown_action_has_no_authority_by_default():
    gate = AuthorityGate()
    assert gate.evaluate("x", ActionRisk.READ, AuthorityLevel.SYSTEM)[0] is False


def test_lower_authority_cannot_escalate():
    gate = AuthorityGate({"deploy": AuthorityPolicy(AuthorityLevel.USER)})
    assert gate.evaluate("deploy", ActionRisk.WRITE, AuthorityLevel.SUPERVISOR)[0] is False


def test_user_can_authorize_irreversible_only_with_explicit_approval():
    gate = AuthorityGate({"publish": AuthorityPolicy(AuthorityLevel.USER)})
    assert gate.evaluate("publish", ActionRisk.IRREVERSIBLE, AuthorityLevel.USER)[0] is False
    assert gate.evaluate("publish", ActionRisk.IRREVERSIBLE, AuthorityLevel.USER, explicit_approval=True)[0] is True


def test_supervisor_cannot_self_authorize_irreversible():
    gate = AuthorityGate({"publish": AuthorityPolicy(AuthorityLevel.USER)})
    assert gate.evaluate("publish", ActionRisk.IRREVERSIBLE, AuthorityLevel.SUPERVISOR, explicit_approval=True)[0] is False

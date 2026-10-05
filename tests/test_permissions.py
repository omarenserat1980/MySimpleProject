from platform_foundation.permissions import ActionRisk, PermissionBoundary


def test_unknown_action_is_denied() -> None:
    boundary = PermissionBoundary({"read_state": ActionRisk.READ})
    decision = boundary.decide("delete_everything", ActionRisk.IRREVERSIBLE)
    assert not decision.allowed


def test_allowlisted_matching_risk_is_allowed() -> None:
    boundary = PermissionBoundary({"write_state": ActionRisk.WRITE})
    decision = boundary.decide("write_state", ActionRisk.WRITE)
    assert decision.allowed


def test_risk_mismatch_is_denied() -> None:
    boundary = PermissionBoundary({"write_state": ActionRisk.WRITE})
    decision = boundary.decide("write_state", ActionRisk.READ)
    assert not decision.allowed


def test_irreversible_is_never_implicitly_allowed() -> None:
    boundary = PermissionBoundary({"publish": ActionRisk.IRREVERSIBLE})
    decision = boundary.decide("publish", ActionRisk.IRREVERSIBLE)
    assert not decision.allowed

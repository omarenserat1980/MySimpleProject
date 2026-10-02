from cloud.public_identity_policy import (
    BLOCKED_PERSONAL_ACTIONS, LegalEntityEvidence, lawful_disclosure_required,
    validate_personal_action, validate_public_operation,
)

def test_public_operation_requires_registration_and_approval():
    evidence = LegalEntityEvidence("reg-1", None, None, None)
    result = validate_public_operation(entity_registered=True, compliance_ready=True, human_approval=False, evidence=evidence)
    assert result["ok"] is False
    assert "human_approval" in result["missing"]

def test_public_operation_requires_registration_evidence():
    result = validate_public_operation(entity_registered=False, compliance_ready=False, human_approval=False, evidence=LegalEntityEvidence(None, None, None, None))
    assert result["ok"] is False
    assert "registration_evidence" in result["missing"]

def test_personal_guarantee_is_blocked_by_default():
    assert "PERSONAL_GUARANTEE" in BLOCKED_PERSONAL_ACTIONS
    assert validate_personal_action("personal_guarantee")["blocked"] is True

def test_normal_brain_operation_is_not_personal_debt():
    assert validate_personal_action("PUBLIC_SERVICE_DELIVERY")["ok"] is True

def test_lawful_disclosure_is_not_public_disclosure():
    assert lawful_disclosure_required("regulator") is True
    assert lawful_disclosure_required("bank") is True
    assert lawful_disclosure_required("customer") is False
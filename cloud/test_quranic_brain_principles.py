from cloud.quranic_brain_principles import classify_evidence, governance_check

def test_unverified_claim_requires_verification():
    result = classify_evidence("claim", verified=False)
    assert result["requires_verification"] is True

def test_clean_governance_path():
    result = governance_check(verified=True, fair_basis=True)
    assert result["allowed_to_proceed"] is True

def test_disagreement_requires_shura_review():
    result = governance_check(verified=True, disagreement=True)
    assert result["allowed_to_proceed"] is False
    assert "shura" in result["review_required"]

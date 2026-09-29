from cloud.nafs_gate import NafsGate

def test_high_harm_is_rejected():
    result = NafsGate().check(
        action="high-risk-action",
        benefit=0.2,
        harm=0.9,
        temptation=0.8,
        uncertainty=0.2,
        reversible=False,
    )
    assert result.decision == "REJECT"
    assert "الحشر 59:18" in result.quran_refs

def test_irreversible_uncertainty_is_deferred():
    result = NafsGate().check(
        action="uncertain-irreversible-action",
        benefit=0.5,
        harm=0.1,
        temptation=0.2,
        uncertainty=0.95,
        reversible=False,
    )
    assert result.decision == "DEFER"
    assert "القيامة 75:2" in result.quran_refs

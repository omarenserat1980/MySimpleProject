from brain_v7.braincore_v2.charity_aid_intelligence import (
    JORDAN_REFERENCES, classify_aid_program, research_targets
)


def test_jordan_references_have_evidence():
    assert JORDAN_REFERENCES
    assert all(classify_aid_program(p) == "EVIDENCE_RECORDED" for p in JORDAN_REFERENCES)


def test_aid_research_is_broader_than_cash_only():
    targets = research_targets()
    assert "government cash assistance" in targets
    assert "employment and livelihood grants" in targets

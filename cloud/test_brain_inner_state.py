from cloud.brain_inner_state import BrainInnerState

def test_inner_state_requires_review_for_high_harm():
    brain = BrainInnerState()
    result = brain.evaluate(
        action="dangerous-action",
        evidence=0.8,
        ambiguity=0.1,
        pressure=0.2,
        social_impact=0.1,
        benefit=0.1,
        harm=0.95,
        temptation=0.8,
        uncertainty=0.2,
        reversible=False,
    )
    assert result["decision"] == "REVIEW"

def test_inner_state_can_proceed_to_authorization():
    brain = BrainInnerState()
    result = brain.evaluate(
        action="safe-reversible-action",
        evidence=0.9,
        ambiguity=0.1,
        pressure=0.0,
        social_impact=0.8,
        benefit=0.8,
        harm=0.0,
        temptation=0.0,
        uncertainty=0.1,
        reversible=True,
    )
    assert result["decision"] == "PROCEED_TO_AUTHORIZATION"

def test_no_literal_claim():
    assert BrainInnerState().audit()["literal_human_inner_state_claim"] is False

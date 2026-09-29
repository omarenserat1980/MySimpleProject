from cloud.heart_engine import HeartEngine

def test_heart_engine_exposes_core_state():
    engine = HeartEngine()
    state = engine.perceive(evidence=0.8, ambiguity=0.2, pressure=0.1, social_impact=0.8)
    assert 0 <= state.clarity <= 1
    assert 0 <= state.openness <= 1

def test_contradiction_triggers_review_pressure():
    engine = HeartEngine()
    result = engine.review(contradiction=0.95, new_evidence=0.0)
    assert result["action"] == "FORCE_REVIEW"

def test_no_literal_spiritual_claim():
    assert HeartEngine().audit()["literal_spiritual_heart_created"] is False

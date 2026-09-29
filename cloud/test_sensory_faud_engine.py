from cloud.sensory_faud_engine import SensoryFuadEngine

def test_hearing_and_vision_are_distinct_observations():
    e = SensoryFuadEngine()
    e.observe("hearing", "door opened", 0.9)
    e.observe("vision", "door closed", 0.8)
    result = e.contradiction(0, 1)
    assert result["detected"] is True
    assert result["requires_review"] is True

def test_interpretation_does_not_overstate_evidence():
    e = SensoryFuadEngine()
    e.observe("vision", "dark corridor", 0.8)
    result = e.integrate(interpretation="someone may be present", confidence=0.9)
    assert result["confidence"] == 0.8
    assert result["distinction"] == "interpretation_not_raw_observation"

def test_no_metaphysical_claim():
    assert SensoryFuadEngine().audit()["literal_spiritual_fuad_created"] is False

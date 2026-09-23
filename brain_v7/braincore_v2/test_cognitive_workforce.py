from brain_v7.braincore_v2.cognitive_workforce import CognitiveWorkforce

def test_review_compares_specialists_and_keeps_alternatives():
    result = CognitiveWorkforce().review("build", [
        {"employee_id":"E1","confidence":0.9,"evidence":3,"reversible":0.9},
        {"employee_id":"E2","confidence":0.5,"evidence":1,"reversible":0.8},
    ])
    assert result["selected"]["employee_id"] == "E1"
    assert len(result["alternatives"]) == 1
    assert result["requires_external_approval"] is True
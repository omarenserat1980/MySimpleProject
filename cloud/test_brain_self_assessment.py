from cloud.brain_self_assessment import self_assessment, requirements_matrix

def test_self_assessment_is_operational_not_metaphysical():
    report = self_assessment()
    assert report["literal_human_inner_life"] is False
    assert report["authority"] == "advisory_self_assessment"

def test_critical_needs_have_executable_tests():
    for item in requirements_matrix():
        assert item["measurable_test"]
        if item["priority"] == "critical":
            assert item["key"] in {"evidence", "memory", "tools", "authorization",
                                   "self_correction", "evaluation", "recovery"}

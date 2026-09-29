from cloud.human_like_benchmark import DIMENSIONS, Evidence, score, validate_dimensions


def test_benchmark_has_fifty_dimensions():
    assert len(DIMENSIONS) == 50
    assert len(set(DIMENSIONS)) == 50


def test_score_requires_evidence():
    assert score([]) == 0.0


def test_pass_and_partial_are_auditable():
    evidence = [Evidence(DIMENSIONS[0], "PASS", "test evidence")]
    evidence += [Evidence(d, "PARTIAL", "test evidence") for d in DIMENSIONS[1:]]
    validate_dimensions(evidence)
    assert score(evidence) == 0.51


def test_unknown_dimension_is_rejected():
    try:
        validate_dimensions([Evidence("invented", "PASS", "x")])
    except ValueError:
        return
    raise AssertionError("unknown benchmark dimension was accepted")


from cloud.human_like_benchmark import benchmark_plan, validate_plan, TARGET_TESTS


def test_plan_totals_5000():
    validate_plan()
    plan = benchmark_plan()
    assert sum(plan.values()) == TARGET_TESTS
    assert len(plan) == len(DIMENSIONS)

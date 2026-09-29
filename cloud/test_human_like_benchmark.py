from cloud.human_like_benchmark import DIMENSIONS, Evidence, score, validate_dimensions


def test_benchmark_has_fourteen_dimensions():
    assert len(DIMENSIONS) == 14
    assert len(set(DIMENSIONS)) == 14


def test_score_requires_evidence():
    assert score([]) == 0.0


def test_pass_and_partial_are_auditable():
    evidence = [Evidence(DIMENSIONS[0], "PASS", "test evidence")]
    evidence += [Evidence(d, "PARTIAL", "test evidence") for d in DIMENSIONS[1:]]
    validate_dimensions(evidence)
    assert score(evidence) == round(100 * (1 + 13 * 0.5) / 14, 2)


def test_unknown_dimension_is_rejected():
    try:
        validate_dimensions([Evidence("invented", "PASS", "x")])
    except ValueError:
        return
    raise AssertionError("unknown benchmark dimension was accepted")

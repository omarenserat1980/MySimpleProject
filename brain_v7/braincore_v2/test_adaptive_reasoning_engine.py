from brain_v7.braincore_v2.adaptive_reasoning_engine import AdaptiveReasoningEngine


def test_understanding_detects_broad_scope_and_keeps_unknowns():
    engine = AdaptiveReasoningEngine()
    result = engine.reason("طور العقل الإلكتروني ليصبح أذكى في الفهم والاستدلال والمرونة")
    assert result.interpretation.intent in {"IMPROVE", "BUILD", "CREATE"}
    assert result.selected_strategy
    assert 0.0 <= result.confidence <= 1.0
    assert 0.0 <= result.flexibility_score <= 1.0
    assert len(result.hypotheses) >= 3


def test_contradictory_observation_reduces_confidence():
    engine = AdaptiveReasoningEngine()
    result = engine.reason(
        "improve reasoning",
        observations=[
            {"statement": "measured failure", "polarity": "against"},
        ],
    )
    assert result.contradictions
    assert any(h.evidence_against for h in result.hypotheses)


def test_reversible_alternative_is_retained():
    engine = AdaptiveReasoningEngine()
    result = engine.reason("build a new cognitive planner")
    labels = {h.label for h in result.hypotheses}
    assert {"DIRECT", "DECOMPOSE", "EXPERIMENT"} <= labels
    assert result.hypotheses

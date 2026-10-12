from brain_v12.youtube.learning_engine import (
    ExpansionAction,
    LearningSnapshot,
    Measurement,
    expansion_gate,
    summarize_learning,
)


def test_measurement_rejects_impossible_metrics():
    try:
        Measurement("x", 10, 11, 20)
    except ValueError as exc:
        assert "views cannot exceed impressions" in str(exc)
    else:
        raise AssertionError("expected invalid metrics to fail")


def test_learning_requires_evidence_before_expansion():
    snapshot = summarize_learning([
        Measurement("a", 1000, 100, 20),
        Measurement("b", 1000, 100, 20),
    ])
    assert snapshot.experiments == 2
    assert expansion_gate(snapshot) is ExpansionAction.CONTINUE


def test_learning_iterates_when_results_are_not_repeated_winners():
    snapshot = LearningSnapshot(
        experiments=5,
        total_impressions=5000,
        total_views=500,
        best_watch_efficiency=2.0,
        repeat_winner_count=1,
    )
    assert expansion_gate(snapshot) is ExpansionAction.ITERATE


def test_learning_allows_expansion_only_after_repeated_signal():
    snapshot = LearningSnapshot(
        experiments=5,
        total_impressions=5000,
        total_views=700,
        best_watch_efficiency=3.0,
        repeat_winner_count=2,
    )
    assert expansion_gate(snapshot) is ExpansionAction.EXPAND

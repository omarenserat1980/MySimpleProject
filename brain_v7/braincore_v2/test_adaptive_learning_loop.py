"""Regression tests for adaptive learning."""
from brain_v7.braincore_v2.adaptive_learning_loop import AdaptiveLearningLoop


def test_success_and_failure_change_strategy_weights():
    loop = AdaptiveLearningLoop()
    initial = loop._get("DIRECT").weight
    loop.record_outcome(cycle=1, objective="x", strategy="DIRECT",
                        outcome="success", reward=1.0, evidence="verified local result")
    good = loop._get("DIRECT").weight
    loop.record_outcome(cycle=2, objective="x", strategy="DIRECT",
                        outcome="failure", reward=-1.0, evidence="explicit failure")
    after = loop._get("DIRECT").weight
    assert good > initial
    assert after < good


def test_unknown_is_not_counted_as_success():
    loop = AdaptiveLearningLoop()
    loop.record_outcome(cycle=1, objective="x", strategy="EXPERIMENT")
    stats = loop._get("EXPERIMENT")
    assert stats.successes == 0
    assert stats.failures == 0
    assert stats.unknowns == 1


def test_recommendation_keeps_alternatives():
    loop = AdaptiveLearningLoop()
    loop.record_outcome(cycle=1, objective="x", strategy="DIRECT",
                        outcome="success", reward=1.0, evidence="ok")
    result = loop.replan(["DIRECT", "DECOMPOSE", "EXPERIMENT"], reason="new evidence")
    assert result["selected"] in {"DIRECT", "DECOMPOSE", "EXPERIMENT"}
    assert len(result["alternatives"]) == 2

def test_negative_reward_is_preserved_in_mean_reward():
    loop = AdaptiveLearningLoop()
    stats = loop.record_outcome(
        cycle=1,
        objective="x",
        strategy="DIRECT",
        outcome="failure",
        reward=-1.0,
        evidence="explicit failure",
    )
    assert stats.mean_reward < 0

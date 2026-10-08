from brain_v12.youtube.channel_strategy import (
    ChannelProfile,
    ExperimentResult,
    choose_experiment,
    evaluate_channel,
)


def test_channel_rejects_weak_originality():
    profile = ChannelProfile("c1", "ar", "ai-stories", 0.9, 0.9, 0.5, 0.9, 0.8, 0.2)
    result = evaluate_channel(profile)
    assert result.viable is False
    assert "LOW_ORIGINALITY_HEADROOM" in result.reasons


def test_channel_can_be_viable():
    profile = ChannelProfile("c2", "ar", "ai-stories", 0.9, 0.9, 0.4, 0.9, 0.8, 0.9)
    result = evaluate_channel(profile)
    assert result.viable is True
    assert result.score >= 0.55


def test_experiment_uses_watch_seconds_per_impression_first():
    results = [
        ExperimentResult("low", 1000, 100, 10, 1),
        ExperimentResult("winner", 1000, 90, 30, 1),
    ]
    assert choose_experiment(results) == "winner"


def test_empty_experiment_set_returns_baseline():
    assert choose_experiment([]) == "BASELINE"

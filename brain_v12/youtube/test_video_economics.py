from brain_v12.youtube.video_economics import (
    VideoEconomicAction,
    VideoEconomics,
    decide_video_economics,
)


def test_high_cost_video_is_killed():
    economics = VideoEconomics("v1", 2, 6, 0, 10000, 5, 0.8)
    result = decide_video_economics(economics)
    assert result.action is VideoEconomicAction.KILL
    assert result.reason == "DIRECT_COST_TOO_HIGH"


def test_positive_expected_value_is_produced():
    economics = VideoEconomics("v2", 2, 1, 0, 10000, 5, 0.8)
    result = decide_video_economics(economics)
    assert result.action is VideoEconomicAction.PRODUCE


def test_learning_experiment_can_be_held_without_claiming_revenue():
    economics = VideoEconomics("v3", 2, 0, 0, 0, 0, 0.0, learning_value=0.9)
    result = decide_video_economics(economics)
    assert result.action is VideoEconomicAction.HOLD
    assert "LEARNING" in result.reason


def test_break_even_views_is_estimate_only():
    economics = VideoEconomics("v4", 2, 2, 1, 10000, 5, 0.5)
    assert economics.break_even_views == 600
    assert economics.expected_ad_value_usd == 25
    assert economics.expected_net_value_usd == 22

from brain_v12.youtube.channel_strategy import ChannelProfile
from brain_v12.youtube.production_gate import evaluate_production_gate
from brain_v12.youtube.revenue_factory import VideoCandidate
from brain_v12.youtube.video_economics import VideoEconomics, VideoEconomicAction


def channel():
    return ChannelProfile("c1", "ar", "ai-stories", 0.9, 0.9, 0.4, 0.9, 0.8, 0.9)


def candidate():
    return VideoCandidate("v1", "ai-stories", "original story", 0.9, 0.1, 0.1, 0.9)


def economics():
    return VideoEconomics("v1", 2, 1, 0, 10000, 5, 0.8, 0.8)


def test_gate_allows_good_video():
    result = evaluate_production_gate(channel(), candidate(), economics())
    assert result.allowed is True
    assert result.reason == "PRODUCTION_ALLOWED"


def test_gate_blocks_nonviable_channel():
    bad = ChannelProfile("c2", "ar", "weak", 0.2, 0.9, 0.4, 0.9, 0.8, 0.9)
    result = evaluate_production_gate(bad, candidate(), economics())
    assert result.allowed is False
    assert result.reason == "CHANNEL_NOT_VIABLE"


def test_gate_blocks_economic_kill():
    expensive = VideoEconomics("v1", 2, 10, 0, 10000, 5, 0.8)
    result = evaluate_production_gate(channel(), candidate(), expensive)
    assert result.allowed is False
    assert result.reason == "VIDEO_ECONOMICS_KILL"


def test_gate_rejects_mismatched_video_ids():
    wrong = VideoEconomics("different", 2, 1, 0, 10000, 5, 0.8)
    try:
        evaluate_production_gate(channel(), candidate(), wrong)
    except ValueError as exc:
        assert "video IDs" in str(exc)
    else:
        raise AssertionError("expected mismatch to fail")

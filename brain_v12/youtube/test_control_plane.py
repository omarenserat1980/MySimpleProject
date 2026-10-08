from brain_v12.youtube.channel_strategy import ChannelProfile
from brain_v12.youtube.content_integrity import ContentFingerprint
from brain_v12.youtube.control_plane import control_video
from brain_v12.youtube.qc_gate import QcReport
from brain_v12.youtube.revenue_factory import VideoCandidate
from brain_v12.youtube.video_economics import VideoEconomics


def sample():
    channel = ChannelProfile("c", "ar", "ai", .9, .9, .4, .9, .8, .9)
    candidate = VideoCandidate("v", "ai", "story", .9, .1, .1, .9)
    economics = VideoEconomics("v", 2, 1, 0, 10000, 5, .8, .8)
    qc = QcReport(True, True, 120, True, True, True, .1)
    fingerprint = ContentFingerprint("v", "ai", "story", "script", "assets")
    return channel, candidate, economics, qc, fingerprint


def test_control_plane_blocks_duplicate():
    args = sample()
    result = control_video(*args, existing_fingerprints=[args[-1]])
    assert result.duplicate is True
    assert result.action == "BLOCK_DUPLICATE"


def test_control_plane_allows_first_video_to_publish_then_measure():
    args = sample()
    result = control_video(*args, existing_fingerprints=[])
    assert result.duplicate is False
    assert result.action == "PUBLISH_THEN_MEASURE"
    assert result.audit.fingerprint()


def test_control_plane_rejects_fingerprint_mismatch():
    channel, candidate, economics, qc, fingerprint = sample()
    wrong = ContentFingerprint("other", "ai", "story", "script", "assets")
    try:
        control_video(channel, candidate, economics, qc, wrong, [])
    except ValueError as exc:
        assert "fingerprint video ID" in str(exc)
    else:
        raise AssertionError("expected fingerprint mismatch to fail")

from brain_v12.youtube.channel_strategy import ChannelProfile
from brain_v12.youtube.lifecycle import evaluate_lifecycle
from brain_v12.youtube.measurement import VideoMeasurement
from brain_v12.youtube.qc_gate import PublishDecision, QcReport
from brain_v12.youtube.revenue_factory import VideoCandidate
from brain_v12.youtube.video_economics import VideoEconomics


def data():
    return (
        ChannelProfile("c", "ar", "ai", .9, .9, .4, .9, .8, .9),
        VideoCandidate("v", "ai", "story", .9, .1, .1, .9),
        VideoEconomics("v", 2, 1, 0, 10000, 5, .8, .8),
    )


def good_qc():
    return QcReport(True, True, 120, True, True, True, .1)


def test_lifecycle_blocks_bad_qc():
    c, v, e = data()
    qc = QcReport(True, False, 120, True, True, True, .1)
    result = evaluate_lifecycle(c, v, e, qc)
    assert result.publish_decision is PublishDecision.BLOCK
    assert result.next_action == "FIX_QC"


def test_lifecycle_requires_measurement_after_publish_gate():
    c, v, e = data()
    result = evaluate_lifecycle(c, v, e, good_qc())
    assert result.publish_decision is PublishDecision.READY
    assert result.next_action == "PUBLISH_THEN_MEASURE"


def test_lifecycle_learns_only_from_matching_measured_video():
    c, v, e = data()
    m = VideoMeasurement("v", 1000, 100, 2000, 5, "2026-10-08T03:00:00Z")
    result = evaluate_lifecycle(c, v, e, good_qc(), m)
    assert result.measurement_quality == "MEASURABLE"
    assert result.next_action == "LEARN_FROM_RESULTS"


def test_lifecycle_rejects_measurement_for_wrong_video():
    c, v, e = data()
    m = VideoMeasurement("other", 1000, 100, 2000, 5, "2026-10-08T03:00:00Z")
    try:
        evaluate_lifecycle(c, v, e, good_qc(), m)
    except ValueError as exc:
        assert "video ID" in str(exc)
    else:
        raise AssertionError("expected mismatched measurement to fail")

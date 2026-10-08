from brain_v12.youtube.revenue_factory import (
    ContentState,
    VideoCandidate,
    rank_video,
    next_content_state,
)


def test_video_rank_rejects_low_originality():
    candidate = VideoCandidate("v1", "arabic-ai", "AI story", 0.9, 0.2, 0.1, 0.2)
    result = rank_video(candidate)
    assert result.selected is False
    assert result.reason == "ORIGINALITY_TOO_LOW"


def test_video_rank_selects_balanced_candidate():
    candidate = VideoCandidate("v2", "arabic-ai", "Original AI story", 0.9, 0.2, 0.1, 0.9)
    result = rank_video(candidate)
    assert result.selected is True
    assert result.score >= 0.55


def test_content_pipeline_requires_qc_before_publish_ready():
    assert next_content_state(ContentState.RENDERED, qc_passed=False) is ContentState.RENDERED
    assert next_content_state(ContentState.RENDERED, qc_passed=True) is ContentState.QC_PASSED
    assert next_content_state(ContentState.QC_PASSED) is ContentState.PUBLISH_READY

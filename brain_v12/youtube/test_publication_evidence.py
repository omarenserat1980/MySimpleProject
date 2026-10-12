from brain_v12.youtube.publication_evidence import (
    PublicationState, classify_provider_result, verify_provider_presence
)

def test_success_requires_youtube_id():
    e=classify_provider_result(
        {"status":"ok","video_id":"yt123"},
        video_id="v1", decision_fingerprint="fp1",
        original_video_ref="/tmp/v.mp4", observed_at="2026-10-08T00:00:00Z",
    )
    assert e.state is PublicationState.PUBLISHED
    assert e.valid()

def test_unknown_upload_is_not_published():
    e=classify_provider_result(
        {"status":"timeout"},
        video_id="v1", decision_fingerprint="fp1",
        original_video_ref="/tmp/v.mp4", observed_at="2026-10-08T00:00:00Z",
    )
    assert e.state is PublicationState.UPLOAD_UNKNOWN
    assert e.youtube_video_id is None

def test_not_found_can_safe_retry():
    state=verify_provider_presence(
        provider_result={"lookup_status":"not_found"},
        expected_video_id="v1", expected_decision_fingerprint="fp1",
    )
    assert state is PublicationState.SAFE_RETRY

def test_mismatched_identity_never_confirms():
    state=verify_provider_presence(
        provider_result={
            "lookup_status":"found",
            "video_id":"other",
            "decision_fingerprint":"fp1",
        },
        expected_video_id="v1", expected_decision_fingerprint="fp1",
    )
    assert state is PublicationState.VERIFYING

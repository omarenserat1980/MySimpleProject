from brain_v7.braincore_v2.youtube_channel_control import YouTubeChannelControl

def test_youtube_policy_gates_irreversible_actions(monkeypatch):
    monkeypatch.delenv("YOUTUBE_CLIENT_ID", raising=False)
    monkeypatch.delenv("YOUTUBE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("YOUTUBE_REFRESH_TOKEN", raising=False)
    control = YouTubeChannelControl()
    assert control.policy("DELETE_VIDEO")["requires_user_approval"] is True
    assert control.policy("UPLOAD_VIDEO")["allowed"] is True
    assert control.snapshot()["credential_storage"] is False

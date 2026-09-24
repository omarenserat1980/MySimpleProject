from brain_v7.braincore_v2.youtube_api_client import YouTubeApiClient


def test_invalid_refresh_token_is_classified(monkeypatch):
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "client")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "refresh")

    class Response:
        status_code = 400
        def json(self):
            return {"error": "invalid_grant"}

    class Client:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, *args, **kwargs):
            return Response()

    import brain_v7.braincore_v2.youtube_api_client as mod
    monkeypatch.setattr(mod.httpx, "Client", lambda *a, **k: Client())

    result = YouTubeApiClient().validate()
    assert result["status"] == "OAUTH_INVALID"
    assert result["code"] == "OAUTH_REFRESH_TOKEN_INVALID"
    assert result["http_status"] == 400

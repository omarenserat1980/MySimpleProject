from fastapi.testclient import TestClient

def test_healthz(monkeypatch):
    monkeypatch.setenv("BRAIN_CONTROL_TOKEN", "test-token")
    import importlib
    import cloud.api_server as api
    importlib.reload(api)
    client = TestClient(api.app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/v1/status").status_code == 401
    assert client.get("/v1/status", headers={"Authorization": "Bearer test-token"}).status_code == 200

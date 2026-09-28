from fastapi.testclient import TestClient


def _client(monkeypatch):
    monkeypatch.setenv("BRAIN_CONTROL_TOKEN", "test-token")
    import importlib
    import cloud.api_server as api
    importlib.reload(api)
    return api, TestClient(api.app)


def test_healthz_and_auth(monkeypatch):
    api, client = _client(monkeypatch)
    assert client.get("/healthz").status_code == 200
    assert client.get("/v1/status").status_code == 401
    response = client.get("/v1/status", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json()["role"] == "self_hosted_render_alternative"


def test_service_registry_and_deploy_gate(monkeypatch, tmp_path):
    api, client = _client(monkeypatch)
    monkeypatch.setattr(api, "STATE", tmp_path)
    monkeypatch.setattr(api, "FILM_JOBS", tmp_path / "film_jobs")
    api.FILM_JOBS.mkdir(parents=True, exist_ok=True)

    headers = {"Authorization": "Bearer test-token"}
    created = client.post(
        "/v1/services",
        headers=headers,
        json={"name": "demo", "image": "nginx:alpine", "port": 8080},
    )
    assert created.status_code == 200
    assert client.get("/v1/services", headers=headers).status_code == 200

    monkeypatch.setenv("BRAIN_DEPLOY_EXECUTOR", "none")
    deploy_response = client.post("/v1/services/demo/deploy", headers=headers)
    assert deploy_response.status_code == 503


def test_film_video_requires_completed_job(monkeypatch, tmp_path):
    api, client = _client(monkeypatch)
    monkeypatch.setattr(api, "STATE", tmp_path)
    monkeypatch.setattr(api, "FILM_JOBS", tmp_path / "film_jobs")
    api.FILM_JOBS.mkdir(parents=True, exist_ok=True)
    job = {"id": "abc123", "status": "RUNNING"}
    (api.FILM_JOBS / "abc123.json").write_text('{"id":"abc123","status":"RUNNING"}', encoding="utf-8")

    response = client.get(
        "/v1/films/abc123/video",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 409


def test_local_android_bridge_auth(monkeypatch):
    monkeypatch.delenv("BRAIN_CONTROL_TOKEN", raising=False)
    import importlib
    import cloud.api_server as api
    importlib.reload(api)
    client = TestClient(api.app)
    response = client.get("/v1/status", headers={"X-BRAIN-Local-App": "1"})
    assert response.status_code == 200


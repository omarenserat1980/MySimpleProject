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
    assert response.json()["role"] == "brain_cloud_native"


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
    client = TestClient(api.app, client=("127.0.0.1", 12345))
    response = client.get("/v1/status", headers={"X-BRAIN-Local-App": "1"})
    assert response.status_code == 200

    remote = TestClient(api.app, client=("10.0.0.5", 12345))
    response = remote.get("/v1/status", headers={"X-BRAIN-Local-App": "1"})
    assert response.status_code == 503



def test_final_video_is_job_scoped(monkeypatch, tmp_path):
    api, _ = _client(monkeypatch)
    output = tmp_path / "output"
    output.mkdir()
    old = output / "old.mp4"
    exact = output / "final.mp4"
    old.write_bytes(b"x" * 2048)
    exact.write_bytes(b"y" * 2048)
    monkeypatch.setenv("FACTORY_OUTPUT_DIR", str(output))
    selected = api._find_final_video({"id": "job-1", "output_dir": str(output)})
    assert selected == exact

    recorded = output / "recorded.mp4"
    recorded.write_bytes(b"z" * 2048)
    selected = api._find_final_video({"id": "job-2", "output_dir": str(output), "video_path": str(recorded)})
    assert selected == recorded


def test_customer_portal_lifecycle_and_financial_gate(monkeypatch, tmp_path):
    api, client = _client(monkeypatch)
    customer_dir = tmp_path / "customer_requests"
    monkeypatch.setattr(api, "CUSTOMER_REQUESTS", customer_dir)

    created = client.post("/api/customers", json={
        "display_name": "Test Customer",
        "customer_type": "COMPANY",
        "legal_entity_name": "Test Customer LLC",
        "registration_id": "REG-001",
        "authorized_representative": "Authorized Person",
        "service": "Workflow automation",
        "need": "Automate intake",
        "marketing_consent": False,
    })
    assert created.status_code == 200
    data = created.json()
    request_id = data["request_id"]
    assert data["lifecycle_state"] == "DISCOVERED"
    assert data["status"] == "READY_FOR_REVIEW"
    customer_record = client.get(f"/api/customers/{request_id}").json()["customer"]
    assert customer_record["customer_type"] == "COMPANY"
    assert customer_record["legal_entity"]["verification_state"] == "REQUIRED"
    assert customer_record["legal_entity"]["registration_id"] == "REG-001"
    assert data["financial_state"] == "NOT_VERIFIED"
    assert data["revenue_state"] == "NOT_REALIZED"

    fetched = client.get(f"/api/customers/{request_id}")
    assert fetched.status_code == 200
    assert fetched.json()["customer"]["consent"]["marketing"] is False

    unauth_approve = client.post(f"/api/customers/{request_id}/approve")
    assert unauth_approve.status_code == 401

    approved = client.post(
        f"/api/customers/{request_id}/approve",
        headers={"Authorization": "Bearer test-token"},
    )
    assert approved.status_code == 200
    customer = approved.json()["customer"]
    assert customer["lifecycle_state"] == "APPROVED"
    assert customer["financial_state"] == "NOT_VERIFIED"
    assert customer["revenue_state"] == "NOT_REALIZED"

    marketing_message = client.post(
        f"/api/customers/{request_id}/message",
        headers={"Authorization": "Bearer test-token"},
        json={"message": "Marketing", "channel": "EMAIL", "purpose": "MARKETING"},
    )
    assert marketing_message.status_code == 200
    assert marketing_message.json()["ok"] is False
    assert marketing_message.json()["gate"]["reason"] == "NO_VALID_CONSENT"

    service_message = client.post(
        f"/api/customers/{request_id}/message",
        headers={"Authorization": "Bearer test-token"},
        json={"message": "Service update", "channel": "EMAIL", "purpose": "SERVICE"},
    )
    assert service_message.status_code == 200
    assert service_message.json()["gate"] == "AUTHORIZED_NOT_SENT"

    financial = client.get(
        f"/api/customers/{request_id}/financial",
        headers={"Authorization": "Bearer test-token"},
    )
    assert financial.status_code == 200
    assert financial.json()["financial_state"] == "NOT_VERIFIED"
    assert financial.json()["revenue_state"] == "NOT_REALIZED"

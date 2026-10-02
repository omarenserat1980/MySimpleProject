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


def test_diwan_approval_api_and_notification_outbox(monkeypatch, tmp_path):
    api, client = _client(monkeypatch)
    monkeypatch.setenv("BRAIN_STATE_DIR", str(tmp_path))
    import cloud.approval_desk as desk
    desk.STATE = tmp_path
    desk.APPROVAL_DIR = tmp_path / "approvals"
    desk.OUTBOX_DIR = tmp_path / "notification_outbox"
    monkeypatch.delenv("BRAIN_SMTP_HOST", raising=False)

    headers = {"Authorization": "Bearer test-token"}
    created = client.post("/v1/diwan/approvals", headers=headers, json={
        "subject": "Production commitment",
        "reason": "External commitment requires human approval.",
        "risk": "HIGH",
        "recipient_email": "owner@example.com",
        "evidence": [{"type": "quote", "ref": "quote-1"}],
    })
    assert created.status_code == 200
    approval = created.json()["approval"]
    approval_id = approval["approval_id"]
    assert approval["status"] == "PENDING"

    inbox = client.get("/v1/diwan/approvals", headers=headers)
    assert inbox.status_code == 200
    assert inbox.json()["approvals"][0]["approval_id"] == approval_id

    decision = client.post(
        f"/v1/diwan/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "actor": "authorized-human", "note": "Evidence reviewed"},
    )
    assert decision.status_code == 200
    assert decision.json()["approval"]["status"] == "APPROVED"

    duplicate = client.post(
        f"/v1/diwan/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "APPROVED", "actor": "authorized-human"},
    )
    assert duplicate.status_code == 409

    notifications = client.get("/v1/diwan/notifications", headers=headers)
    assert notifications.status_code == 200
    assert notifications.json()["notifications"][0]["status"] == "QUEUED"


def test_diwan_case_and_correspondence_routes(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import cloud.api_server as api
    api.STATE = tmp_path
    api.DIWAN_STATE = tmp_path / "diwan"
    api.DIWAN_STATE.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(api, "TOKEN", "test-token")
    client = TestClient(api.app)
    headers = {"Authorization": "Bearer test-token"}

    case = client.post("/v1/diwan/cases", json={
        "title": "Test case", "owner_type": "CUSTOMER", "owner_id": "cust-1"
    }, headers=headers)
    assert case.status_code == 200
    case_id = case.json()["case"]["case_id"]

    corr = client.post("/v1/diwan/correspondence", json={
        "direction": "INBOUND",
        "subject": "Test request",
        "channel": "EMAIL",
        "sender": "example@example.invalid",
        "case_id": case_id
    }, headers=headers)
    assert corr.status_code == 200
    item = corr.json()["correspondence"]
    assert item["number"].startswith("IN-")
    assert item["state"] == "LINKED"

    listed = client.get("/v1/diwan/correspondence", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()["correspondence"]) == 1


def test_standing_authorization_customer_consent_api_gate(monkeypatch, tmp_path):
    from cloud.standing_authorization import (
        ApprovalStatus, CustomerConsent, Risk, StandingAuthorization,
        customer_gate, execution_gate, operator_gate,
    )
    auth = StandingAuthorization(enabled=True, monetary_limit=100, currency="JOD")
    op = operator_gate(authorization=auth, risk=Risk.ROUTINE, amount=50, currency="JOD")
    assert op == ApprovalStatus.NOT_REQUIRED
    consent = CustomerConsent(
        approved=True, scope_ref="QUOTE-1", approved_version="v1",
        approved_amount=50, approved_currency="JOD", evidence_ref="consent-1",
    )
    customer = customer_gate(
        required=True, consent=consent, scope_ref="QUOTE-1", version="v1",
        amount=50, currency="JOD",
    )
    assert customer == ApprovalStatus.APPROVED
    assert execution_gate(operator_status=op, customer_status=customer)


def test_standing_authorization_blocks_over_limit_and_scope_mismatch():
    from cloud.standing_authorization import (
        ApprovalStatus, CustomerConsent, Risk, StandingAuthorization,
        customer_gate, operator_gate,
    )
    auth = StandingAuthorization(enabled=True, monetary_limit=100, currency="JOD")
    assert operator_gate(authorization=auth, risk=Risk.ROUTINE, amount=101, currency="JOD") == ApprovalStatus.REQUIRED
    consent = CustomerConsent(
        approved=True, scope_ref="QUOTE-1", approved_version="v1",
        approved_amount=50, approved_currency="JOD", evidence_ref="consent-1",
    )
    assert customer_gate(required=True, consent=consent, scope_ref="QUOTE-2", version="v1", amount=50, currency="JOD") == ApprovalStatus.REQUIRED


def test_customer_feedback_api_lifecycle_and_evidence(monkeypatch, tmp_path):
    api, client = _client(monkeypatch)
    feedback_dir = tmp_path / "customer_feedback"
    monkeypatch.setattr(api, "FEEDBACK_STATE", feedback_dir)
    feedback_dir.mkdir(parents=True, exist_ok=True)

    created = client.post("/v1/feedback", json={
        "customer_id": "cust-1",
        "rating": 4,
        "category": "QUALITY",
        "body": "Good service, but response was slow.",
        "consent_to_contact": True,
        "marketing_consent": False,
    })
    assert created.status_code == 200
    feedback_id = created.json()["feedback_id"]
    assert created.json()["state"] == "RECEIVED"

    headers = {"Authorization": "Bearer test-token"}
    fetched = client.get(f"/v1/feedback/{feedback_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["customer_id"] == "cust-1"

    triaged = client.post(
        f"/v1/feedback/{feedback_id}/transition",
        headers=headers,
        params={"state": "TRIAGED"},
    )
    assert triaged.status_code == 200

    unresolved = client.post(
        f"/v1/feedback/{feedback_id}/transition",
        headers=headers,
        params={"state": "RESOLVED"},
    )
    assert unresolved.status_code == 422

    resolved = client.post(
        f"/v1/feedback/{feedback_id}/transition",
        headers=headers,
        params={"state": "RESOLVED", "evidence_ref": "case://feedback/verified-1"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["state"] == "RESOLVED"

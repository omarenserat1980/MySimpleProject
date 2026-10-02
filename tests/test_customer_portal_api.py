from brain_v12.customer_portal_api import LeadIn, LeadStore, create_app
from brain_v12.customer_cases import CustomerCaseStore


def test_lead_is_durable_and_hashed(tmp_path):
    path = tmp_path / "portal.db"
    store = LeadStore(path)
    lead = store.create(LeadIn(name="Test Customer", email="customer@example.com",
                               service="Brain Cloud", details="Need a portal",
                               marketing_consent=True))
    restored = LeadStore(path).get(lead.id)
    assert restored.status == "NEW"
    assert restored.marketing_consent is True
    assert len(restored.content_hash) == 64


def test_case_and_approval_api(tmp_path):
    from fastapi.testclient import TestClient
    client = TestClient(create_app(
        LeadStore(tmp_path / "portal.db"),
        CustomerCaseStore(tmp_path / "cases.db"),
    ))
    lead = client.post("/v1/leads", json={
        "name": "Test", "email": "test@example.com",
        "service": "Brain Cloud", "details": "Portal"
    }).json()
    assert lead["case_id"] is not None
    case = client.get(f"/v1/cases/{lead['case_id']}")
    assert case.status_code == 200
    approval = client.post(f"/v1/cases/{lead['case_id']}/approval")
    assert approval.status_code == 201
    decision = client.post(f"/v1/approvals/{approval.json()['id']}/decision",
                           json={"actor": "operator", "approved": True, "note": "reviewed"})
    assert decision.status_code == 200
    assert decision.json()["status"] == "APPROVED"


def test_health_endpoint(tmp_path):
    from fastapi.testclient import TestClient
    client = TestClient(create_app(LeadStore(tmp_path / "portal.db"),
                                   CustomerCaseStore(tmp_path / "cases.db")))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

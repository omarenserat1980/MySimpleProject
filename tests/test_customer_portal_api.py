from brain_v12.customer_portal_api import LeadIn, LeadStore, create_app


def test_lead_is_durable_and_hashed(tmp_path):
    path = tmp_path / "portal.db"
    store = LeadStore(path)
    lead = store.create(
        LeadIn(
            name="Test Customer",
            email="customer@example.com",
            service="Brain Cloud",
            details="Need a portal",
            marketing_consent=True,
        )
    )
    restored = LeadStore(path).get(lead.id)
    assert restored.status == "NEW"
    assert restored.marketing_consent is True
    assert len(restored.content_hash) == 64


def test_health_endpoint():
    from fastapi.testclient import TestClient
    client = TestClient(create_app(LeadStore(":memory:")))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

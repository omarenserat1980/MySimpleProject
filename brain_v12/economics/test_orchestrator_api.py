from fastapi.testclient import TestClient

from economics.orchestrator_api import router


def test_api_returns_hold_for_new_class():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/api/economics/orchestrator/evaluate",
        json={
            "opportunity_id": "api-1",
            "opportunity_class": "new_class",
            "expected_pay": 100,
            "acceptance_probability": 0.8,
            "brain_assistance": 0.8,
            "time_hours": 2,
            "entry_friction": 0.1,
            "risk": 0.1,
            "eligibility": ["Jordan", "remote"],
            "upfront_cost_usd": 0,
            "source_url": "https://example.com/job",
            "last_verified_at": "2026-10-08T00:00:00Z",
            "observations": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "HOLD"
    assert data["side_effects"] is False


def test_api_rejects_invalid_upfront_cost():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/api/economics/orchestrator/evaluate",
        json={
            "opportunity_id": "api-2",
            "opportunity_class": "video",
            "expected_pay": 100,
            "acceptance_probability": 0.8,
            "brain_assistance": 0.8,
            "time_hours": 2,
            "entry_friction": 0.1,
            "risk": 0.1,
            "eligibility": ["Jordan"],
            "upfront_cost_usd": 5,
            "source_url": "https://example.com/job",
            "last_verified_at": "2026-10-08T00:00:00Z",
            "observations": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "REJECT"

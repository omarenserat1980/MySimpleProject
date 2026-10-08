from fastapi.testclient import TestClient
from economics.api import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_score_endpoint():
    r = client.post("/api/economics/score", json={
        "opportunity_id": "x", "expected_pay": 100,
        "acceptance_probability": .5, "brain_assistance": .8,
        "time_hours": 2, "entry_friction": .1, "risk": .1
    })
    assert r.status_code == 200
    assert r.json()["score"] > 0


def test_revenue_endpoint_requires_proof():
    r = client.post("/api/economics/revenue/verify", json={
        "evidence_id": "e", "opportunity_id": "x", "amount": 20,
        "currency": "USD", "received_at": "2026-10-08T01:00:00Z",
        "proof_ref": ""
    })
    assert r.status_code == 422

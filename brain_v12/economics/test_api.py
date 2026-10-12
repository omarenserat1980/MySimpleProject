from fastapi.testclient import TestClient
from fastapi import FastAPI

from brain_v12.economics.api import router

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


def test_revenue_endpoint_does_not_claim_payment_verified():
    r = client.post("/api/economics/revenue/verify", json={
        "evidence_id": "e-1", "opportunity_id": "opp-1", "amount": 20,
        "currency": "USD", "received_at": "2026-10-08T01:00:00Z",
        "proof_ref": "receipt://reference-only"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "EVIDENCE_FORMAT_VALIDATED_NOT_PAYMENT_VERIFIED"
    assert body["revenue_claimed"] is False
    assert body["side_effects"] is False
    assert "no independent" in body["verification_scope"]


def test_revenue_endpoint_rejects_blank_evidence_identity():
    r = client.post("/api/economics/revenue/verify", json={
        "evidence_id": " ", "opportunity_id": "opp-1", "amount": 20,
        "currency": "USD", "received_at": "2026-10-08T01:00:00Z",
        "proof_ref": "receipt://reference-only"
    })
    assert r.status_code == 422

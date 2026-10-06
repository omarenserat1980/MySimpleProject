from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.synthetic_customer import SyntheticCustomer
from brain_v12.synthetic_customer_api import router


def _customer():
    def advisor_a(request, capabilities):
        return {
            "summary": "ChatGPT test proposal",
            "scope": ["safe test delivery"],
            "risks": ["bounded test only"],
            "acceptance": ["verified result"],
        }

    def advisor_b(request, capabilities):
        return {
            "summary": "Brain test proposal",
            "scope": ["safe test delivery"],
            "risks": ["no production"],
            "acceptance": ["evidence recorded"],
        }

    def executor(request, customer_type, run_id):
        return {"ok": True, "verified": True, "artifact": "local-test-artifact"}

    return SyntheticCustomer(
        chatgpt_advisor=advisor_a,
        brain_advisor=advisor_b,
        executor=executor,
    )


def test_local_api_wiring_and_safety_gate():
    customer = _customer()
    app = FastAPI()
    app.include_router(router(customer, lambda: {
        "capabilities": {"synthetic_customer": True},
        "tools": ["local-test"],
        "engines": ["test-engine"],
    }))
    client = TestClient(app)

    plan = client.get("/api/synthetic-customer/suite/plan")
    assert plan.status_code == 200
    assert plan.json()["suite"]["scenario_count"] >= 7
    assert plan.json()["suite"]["production_allowed"] is False

    suite = client.post("/api/synthetic-customer/suite/run?limit=2")
    assert suite.status_code == 200
    assert suite.json()["ok"] is True
    assert suite.json()["count"] == 2
    assert all(item["proposal_ready"] for item in suite.json()["results"])

    created = client.post(
        "/api/synthetic-customer/runs",
        json={
            "customer_type": "TEST_CUSTOMER_SOFTWARE",
            "request": "Build a safe test utility.",
        },
    )
    assert created.status_code == 200
    run_id = created.json()["run"]["run_id"]
    assert set(created.json()["proposals"]["unified"]["sources"]) == {"CHATGPT", "BRAIN"}

    blocked = client.post(
        f"/api/synthetic-customer/runs/{run_id}/execute",
        json={"environment": "TEST", "payment_mode": "NONE"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"] == "CUSTOMER_APPROVAL_REQUIRED"

    approved = client.post(f"/api/synthetic-customer/runs/{run_id}/approve")
    assert approved.status_code == 200

    executed = client.post(
        f"/api/synthetic-customer/runs/{run_id}/execute",
        json={"environment": "SANDBOX", "payment_mode": "TEST"},
    )
    assert executed.status_code == 200
    assert executed.json()["ok"] is True
    assert executed.json()["run"]["status"] == "VERIFIED"

    production = client.post(
        "/api/synthetic-customer/payment-safety"
        "?environment=PRODUCTION&payment_mode=PRODUCTION"
    )
    assert production.status_code == 200
    assert production.json()["allowed"] is False
    assert production.json()["reason"] == "PAYMENT_SAFETY_GATE_BLOCKED"

    print("LOCAL_SYNTHETIC_CUSTOMER_API_GATE=VERIFIED")

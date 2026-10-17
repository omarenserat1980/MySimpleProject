"""HTTP regression tests for the offline mining compatibility contract."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.mining_node_api import router as mining_node_router
from brain_v12.brain.bitcoin_worker_api import router as worker_router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(mining_node_router)
    app.include_router(worker_router)
    return TestClient(app)


def test_simulation_contract_is_offline_and_never_claims_live_mining() -> None:
    with _client() as client:
        response = client.get("/api/mining-node/simulation-contract")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PASS"
    assert body["checks_passed"] == body["checks_total"] == 6
    assert body["network_access_performed"] is False
    assert body["real_mining_verified"] is False
    assert body["revenue_verified"] is False


def test_pool_evidence_status_is_read_only_and_does_not_query_pool() -> None:
    with _client() as client:
        response = client.get("/api/mining-node/pool-evidence/status")
    assert response.status_code == 200
    body = response.json()
    assert body["network_access_performed"] is False
    assert body["pool_query_performed"] is False
    assert body["pool_settings_changed"] is False
    assert body["revenue_verified"] is False


def test_worker_status_fails_closed_without_worker_api_token(monkeypatch) -> None:
    monkeypatch.delenv("BRAIN_MINING_WORKER_API_TOKEN", raising=False)
    with _client() as client:
        response = client.get("/api/bitcoin-mining/worker/status")
    assert response.status_code == 503

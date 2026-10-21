from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain import ckpool_readonly_api


def test_status_endpoint_returns_read_only_evidence(monkeypatch):
    monkeypatch.setattr(
        ckpool_readonly_api,
        "collect_ckpool_readonly",
        lambda: {
            "schema": "electronic-brain.ckpool-readonly.v1",
            "pool_stats_available": True,
            "pool_stats": [{"Workers": 5}],
            "local_miner_started": False,
            "local_hashrate_verified": False,
            "revenue_realized": False,
            "financial_execution_enabled": False,
        },
    )
    app = FastAPI()
    app.include_router(ckpool_readonly_api.router)
    response = TestClient(app).get("/api/mining/ckpool/status")
    assert response.status_code == 200
    body = response.json()
    assert body["pool_stats_available"] is True
    assert body["local_miner_started"] is False
    assert body["revenue_realized"] is False
    assert body["financial_execution_enabled"] is False


def test_status_endpoint_does_not_hide_collection_failure(monkeypatch):
    monkeypatch.setattr(
        ckpool_readonly_api,
        "collect_ckpool_readonly",
        lambda: {
            "schema": "electronic-brain.ckpool-readonly.v1",
            "pool_stats_available": False,
            "pool_stats": None,
            "pool_error": "TimeoutError",
            "local_miner_started": False,
            "revenue_realized": False,
        },
    )
    app = FastAPI()
    app.include_router(ckpool_readonly_api.router)
    body = TestClient(app).get("/api/mining/ckpool/status").json()
    assert body["pool_stats_available"] is False
    assert body["pool_error"] == "TimeoutError"
    assert body["revenue_realized"] is False

from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain import mining_readiness_api as api


def test_readiness_endpoint_fails_closed_without_device_or_payout(monkeypatch):
    monkeypatch.setattr(api, "collect_asic_status", lambda: {
        "ok": True, "state": "WAITING_FOR_EXPLICIT_PRIVATE_IP", "device_contacted": False,
        "network_scan_performed": False, "mining_started": False,
    })
    monkeypatch.setattr(api, "_load_ckpool_evidence", lambda: {
        "stratum_probe": {"tcp_connected": True, "subscription_response_present": True},
        "pool_telemetry": {"pool_stats_available": True},
    })
    monkeypatch.delenv("BRAIN_BTC_PAYOUT_ADDRESS", raising=False)
    app = FastAPI()
    app.include_router(api.router)
    response = TestClient(app).get("/api/mining/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "BLOCKED"
    assert data["real_mining_verified"] is False
    assert data["revenue_realized"] is False
    assert "PAYOUT_ADDRESS_NOT_CONFIGURED" in data["blockers"]
    assert all(v is False for v in data["side_effects"].values())
    assert "BRAIN_BTC_PAYOUT_ADDRESS" not in response.text


def test_bad_or_missing_evidence_file_is_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "_EVIDENCE_PATH", tmp_path / "missing.json")
    assert api._load_ckpool_evidence() == {}
    p = tmp_path / "broken.json"
    p.write_text("{", encoding="utf-8")
    monkeypatch.setattr(api, "_EVIDENCE_PATH", p)
    assert api._load_ckpool_evidence() == {}

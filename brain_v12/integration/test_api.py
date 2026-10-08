from fastapi.testclient import TestClient
from brain_v12.integration.api import build_router
from fastapi import FastAPI

def test_mission_api_is_read_only_planning():
    app=FastAPI()
    app.include_router(build_router())
    c=TestClient(app)
    r=c.post("/api/mission/plan",json={"mission":"Amazon investment","evidence_confidence":.9})
    assert r.status_code==200
    data=r.json()
    assert data["ok"] is True
    assert "commerce" in data["specialists"]
    assert data["action"]=="ANALYZE"
    assert data["decision_evidence_valid"] is True
    assert len(data["decision_evidence_fingerprint"])==64

def test_mission_api_blocks_external_side_effect():
    app=FastAPI()
    app.include_router(build_router())
    c=TestClient(app)
    r=c.post("/api/mission/plan",json={"mission":"publish listing","evidence_confidence":.9,"external_side_effects":True})
    assert r.status_code==200
    assert r.json()["action"]=="AUTHORIZATION_REQUIRED"

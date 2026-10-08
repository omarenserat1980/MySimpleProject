from fastapi.testclient import TestClient
from brain_v12.app import app

def test_intelligence_route_exists():
    r=TestClient(app).post("/api/intelligence/evaluate",json={
        "signals":[{"domain":"economic","confidence":.9,"evidence_count":2,"risk":.1}]
    })
    assert r.status_code==200
    assert r.json()["action"]=="SCENARIO"
    assert r.json()["external_side_effects"] is False

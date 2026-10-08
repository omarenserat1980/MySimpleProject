from fastapi import FastAPI
from fastapi.testclient import TestClient
from brain_v12.marketing.router_bundle import router

def test_marketing_api_is_read_only():
    app=FastAPI()
    app.include_router(router)
    c=TestClient(app)
    r=c.post("/api/marketing/expert/evaluate",json={"question":"Should we test SEO?"})
    assert r.status_code==200
    data=r.json()
    assert data["action"]=="RESEARCH"
    assert data["external_side_effects"] is False

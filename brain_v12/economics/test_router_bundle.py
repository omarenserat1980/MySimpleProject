from fastapi import FastAPI
from fastapi.testclient import TestClient

from economics.router_bundle import router


def test_router_bundle_mounts():
    app = FastAPI()
    app.include_router(router)
    paths = {route.path for route in app.routes}
    assert "/api/economics/score" in paths
    assert "/api/economics/revenue/verify" in paths
    assert "/api/economics/orchestrator/evaluate" in paths


def test_router_bundle_has_no_startup_side_effects():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/docs").status_code == 200

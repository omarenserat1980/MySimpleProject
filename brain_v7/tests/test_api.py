import os
os.environ["BRAIN_DB"] = ":memory:"
from fastapi.testclient import TestClient
from main import app, PERMISSIONS

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True

def test_permissions():
    r = client.get("/api/permissions")
    assert r.status_code == 200
    assert set(r.json()["permissions"]) == {"READ","WRITE","EXECUTE","NETWORK","SYSTEM"}

def test_set_permission():
    r = client.post("/api/permissions", json={"name":"READ","enabled":True})
    assert r.status_code == 200
    assert r.json()["enabled"] is True
    assert PERMISSIONS["READ"] is True

def test_unknown_permission():
    r = client.post("/api/permissions", json={"name":"ROOT","enabled":True})
    assert r.status_code == 200
    assert r.json()["ok"] is False

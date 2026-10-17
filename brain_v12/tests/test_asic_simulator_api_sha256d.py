from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from brain_v12.brain.asic_resource_adapter import ASICResource, ASICResourceAdapter
from brain_v12.brain.asic_simulator_api import router


def make_client(*, wired=True):
    app = FastAPI()
    if wired:
        adapter = ASICResourceAdapter()
        app.state.brain_supervisor = SimpleNamespace(asic_resources=adapter)
    app.include_router(router)
    return TestClient(app)


def request_payload(**overrides):
    payload = {
        "header_hex": "00" * 80,
        "target_hex": "ff" * 32,
        "start_nonce": 7,
        "max_attempts": 1,
        "resource_id": "api-sha256d-sim",
    }
    payload.update(overrides)
    return payload


def test_sha256d_pow_api_uses_brain_supervisor_and_returns_simulation_evidence():
    response = make_client().post("/api/asic-sim/sha256d-pow", json=request_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["execution_mode"] == "SIMULATOR"
    assert body["result"]["result"]["found"] is True
    assert body["result"]["result"]["nonce"] == 7
    assert body["result"]["software_hashing_performed"] is True
    assert body["result"]["rtl_executed"] is False
    assert body["result"]["physical_asic_executed"] is False
    assert body["result"]["pool_contacted"] is False
    assert body["result"]["share_submitted"] is False
    assert body["result"]["pool_acceptance_verified"] is False
    assert body["result"]["revenue_verified"] is False
    assert body["evidence_verification"] == "VERIFIED"


def test_sha256d_pow_api_fails_closed_when_supervisor_is_not_wired():
    response = make_client(wired=False).post(
        "/api/asic-sim/sha256d-pow", json=request_payload()
    )
    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "BRAIN_ASIC_RUNTIME_NOT_WIRED"


def test_sha256d_pow_api_does_not_run_on_non_simulator_resource():
    app = FastAPI()
    adapter = ASICResourceAdapter()
    adapter.register(ASICResource("remote", execution_mode="REMOTE_PROVIDER"))
    app.state.brain_supervisor = SimpleNamespace(asic_resources=adapter)
    app.include_router(router)
    response = TestClient(app).post(
        "/api/asic-sim/sha256d-pow",
        json=request_payload(resource_id="remote"),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["status"] == "SIMULATION_MODE_REQUIRED"


@pytest.mark.parametrize(
    ("overrides", "expected_status"),
    [
        ({"header_hex": "00"}, 422),
        ({"target_hex": "zz"}, 422),
        ({"max_attempts": 1_000_001}, 422),
        ({"start_nonce": -1}, 422),
    ],
)
def test_sha256d_pow_api_validates_bounds(overrides, expected_status):
    response = make_client().post(
        "/api/asic-sim/sha256d-pow", json=request_payload(**overrides)
    )
    assert response.status_code == expected_status


def test_sha256d_rtl_api_reports_only_evidence_gated_rtl_success(monkeypatch):
    import brain_v12.brain.asic_resource_adapter as adapter_module

    monkeypatch.setattr(adapter_module, "run_sha256d_rtl_self_test", lambda **kwargs: {
        "contract_version": "brain.sha256d.execution.v1",
        "execution_mode": "RTL_SIMULATION",
        "status": "VERIFIED",
        "rtl_executed": True,
        "evidence_status": "RTL_SIMULATION_VERIFIED",
        "physical_asic_executed": False,
        "pool_contacted": False,
        "share_submitted": False,
        "pool_acceptance_verified": False,
        "revenue_verified": False,
    })
    response = make_client().post("/api/asic-sim/sha256d-rtl-self-test", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "RTL_SIMULATION_VERIFIED"
    assert body["result"]["execution_mode"] == "RTL_SIMULATION"
    assert body["result"]["rtl_executed"] is True
    assert body["result"]["physical_asic_executed"] is False
    assert body["evidence_verification"] == "VERIFIED"


def test_sha256d_rtl_api_does_not_claim_success_when_toolchain_is_missing(monkeypatch):
    import brain_v12.brain.asic_resource_adapter as adapter_module

    monkeypatch.setattr(adapter_module, "run_sha256d_rtl_self_test", lambda **kwargs: {
        "contract_version": "brain.sha256d.execution.v1",
        "execution_mode": "RTL_SIMULATION",
        "status": "BLOCKED_TOOLCHAIN_UNAVAILABLE",
        "rtl_executed": False,
        "evidence_status": "BLOCKED",
    })
    response = make_client().post("/api/asic-sim/sha256d-rtl-self-test", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["status"] == "BLOCKED_TOOLCHAIN_UNAVAILABLE"
    assert body["result"]["rtl_executed"] is False
    assert body["evidence_ref"] is None

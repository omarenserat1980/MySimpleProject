from pathlib import Path

import pytest
from fastapi import HTTPException

import brain_v12.brain.mining_node_api as api
from brain_v12.business.mining_activity_ledger import MiningActivityLedger


class _Request:
    pass


def test_activity_api_records_without_payout_proof_and_keeps_estimate_unverified(monkeypatch, tmp_path):
    db_path = tmp_path / "mining-activity.db"
    monkeypatch.setattr(api, "require_control_key", lambda request: None)
    monkeypatch.setattr(api, "MiningActivityLedger", lambda: MiningActivityLedger(db_path))

    result = api.record_mining_activity(_Request(), {
        "activity_id": "api-activity-1",
        "run_id": "api-run-1",
        "mode": "SIMULATION",
        "activity_type": "SHA256D_RESULT",
        "payload": {"hashes_tested": 64},
        "estimated_amount": "0.000001",
        "estimated_currency": "BTC",
    })

    assert result["activity_status"] == "SIMULATION_RECORDED"
    assert result["income_status"] == "ESTIMATE_ONLY"
    assert result["counts_as_verified_revenue"] is False


def test_activity_api_requires_control_key(monkeypatch):
    def reject(_request):
        raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr(api, "require_control_key", reject)
    with pytest.raises(HTTPException) as exc:
        api.record_mining_activity(_Request(), {
            "activity_id": "blocked-activity", "run_id": "blocked-run",
            "mode": "SIMULATION", "activity_type": "SIMULATOR_RUN", "payload": {},
        })
    assert exc.value.status_code == 403


def test_activity_api_reads_persisted_record_and_returns_404_for_missing(monkeypatch, tmp_path):
    db_path = tmp_path / "mining-activity.db"
    monkeypatch.setattr(api, "require_control_key", lambda request: None)
    monkeypatch.setattr(api, "MiningActivityLedger", lambda: MiningActivityLedger(db_path))
    api.record_mining_activity(_Request(), {
        "activity_id": "api-activity-2", "run_id": "api-run-2",
        "mode": "LIVE", "activity_type": "HASHRATE_MEASUREMENT",
        "source": "worker-telemetry", "payload": {"hashrate_hs": 100},
    })

    loaded = api.get_mining_activity(_Request(), "api-activity-2")
    assert loaded["activity_status"] == "LIVE_ACTIVITY_UNVERIFIED"
    assert loaded["counts_as_verified_revenue"] is False

    with pytest.raises(HTTPException) as exc:
        api.get_mining_activity(_Request(), "does-not-exist")
    assert exc.value.status_code == 404


def test_activity_routes_are_post_and_authenticated_get():
    routes = {
        route.path: route.methods
        for route in api.router.routes
        if getattr(route, "path", None) in {
            "/api/mining-node/activity",
            "/api/mining-node/activity/{activity_id}",
        }
    }
    assert routes["/api/mining-node/activity"] == {"POST"}
    assert routes["/api/mining-node/activity/{activity_id}"] == {"GET"}


def test_cpu_benchmark_endpoint_is_authenticated_bounded_and_records_activity(monkeypatch, tmp_path):
    db_path = tmp_path / "cpu-benchmark.db"
    monkeypatch.setattr(api, "require_control_key", lambda request: None)
    monkeypatch.setattr(api, "MiningActivityLedger", lambda: MiningActivityLedger(db_path))
    result = api.run_cpu_sha256d_benchmark(_Request(), {
        "activity_id": "api-cpu-bench",
        "run_id": "api-cpu-bench-run",
        "header_prefix_hex": bytes(76).hex(),
        "hashes_per_sample": 8,
        "repeats": 2,
    })
    assert result["measurement"]["execution"] == "host_cpu_software"
    assert result["measurement"]["is_live_mining"] is False
    assert result["activity"]["activity_type"] == "HASHRATE_MEASUREMENT"
    assert result["activity"]["counts_as_verified_revenue"] is False
    assert api.get_mining_activity(_Request(), "api-cpu-bench")["income_status"] == "NO_REVENUE_CLAIM"


def test_cpu_benchmark_endpoint_rejects_unbounded_and_invalid_inputs(monkeypatch):
    monkeypatch.setattr(api, "require_control_key", lambda request: None)
    base = {
        "activity_id": "invalid-cpu-bench",
        "run_id": "invalid-cpu-bench-run",
        "header_prefix_hex": bytes(76).hex(),
    }
    with pytest.raises(HTTPException) as exc:
        api.run_cpu_sha256d_benchmark(_Request(), {**base, "hashes_per_sample": 100_001})
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        api.run_cpu_sha256d_benchmark(_Request(), {**base, "header_prefix_hex": "bad"})
    assert exc.value.status_code == 400


def test_cpu_benchmark_endpoint_requires_control_key(monkeypatch):
    def reject(_request):
        raise HTTPException(status_code=403, detail="forbidden")
    monkeypatch.setattr(api, "require_control_key", reject)
    with pytest.raises(HTTPException) as exc:
        api.run_cpu_sha256d_benchmark(_Request(), {})
    assert exc.value.status_code == 403


def test_cpu_benchmark_route_is_post_only():
    route = next(route for route in api.router.routes if getattr(route, "path", None) == "/api/mining-node/cpu-sha256d-benchmark")
    assert route.methods == {"POST"}

from datetime import datetime, timedelta, timezone

import pytest

from brain_v12.brain.asic_resource_adapter import ASICResource, ASICResourceAdapter


def test_simulator_is_registered_as_simulation_and_never_claims_real_mining():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("sim-1", hashrate=100, hashrate_unit="TH", power_watts=3000))
    assert brain.select({"asic.simulate"})[0]["executor_id"] == "asic:sim-1"

    report = brain.simulate("sim-1", duration_seconds=10)
    assert report["task"]["status"] == "COMPLETED"
    assert report["result"]["estimated_hashes"] == 1_000_000_000_000_000
    assert report["result"]["real_device_measurement"] is False
    assert report["result"]["revenue_verified"] is False
    assert report["evidence_verification"] == "VERIFIED"
    assert brain.resource_snapshot("sim-1")["verification_status"] == "SIMULATED"
    assert brain.release_gate("sim-1")["status"] == "BLOCKED"


def test_remote_provider_data_does_not_become_verified_from_registration_or_hash():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("remote-1", execution_mode="REMOTE_PROVIDER", provider="Example"))
    assert brain.check_health("remote-1")["reason"] == "HEARTBEAT_MISSING"

    evidence = brain.record_telemetry("remote-1", {
        "heartbeat": datetime.now(timezone.utc).isoformat(),
        "pool_status": "CONNECTED",
        "hashrate": 100,
    })
    assert evidence["verification_status"] == "EVIDENCE_HASH_VERIFIED_UNATTESTED"
    assert brain.resource_snapshot("remote-1")["verification_status"] != "VERIFIED"
    assert brain.check_health("remote-1")["health_status"] == "AVAILABLE_UNVERIFIED"
    assert not brain.select({"asic.simulate"})
    gate = brain.release_gate("remote-1")
    assert gate["status"] == "BLOCKED"
    assert "EXTERNAL_IDENTITY_ATTESTATION_REQUIRED" in gate["failures"]
    assert gate["publish_or_activate"] is False


def test_physical_resource_cannot_use_simulator_path():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("device-1", execution_mode="PHYSICAL_DEVICE", device_model="S21"))
    with pytest.raises(PermissionError, match="SIMULATION_MODE_REQUIRED"):
        brain.simulate("device-1")


def test_simulator_cannot_record_real_device_telemetry():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("sim-2"))
    with pytest.raises(PermissionError, match="REAL_RESOURCE_MODE_REQUIRED"):
        brain.record_telemetry("sim-2", {"hashrate": 100})


def test_economic_result_remains_input_based_and_unverified():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("sim-econ", hashrate=100, power_watts=3000, power_cost=0.1))
    result = brain.analyze_economics(
        "sim-econ", gross_revenue_jod_per_day=1.0
    )
    assert result["live_market_data"] is False
    assert result["revenue_verification"] == "UNVERIFIED"
    assert result["actual_revenue_verified"] is False
    assert result["execution_mode"] == "SIMULATOR"


def test_stale_external_heartbeat_is_unhealthy():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("remote-stale", execution_mode="REMOTE_PROVIDER"))
    resource = brain.resources["remote-stale"]
    resource.heartbeat = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    assert brain.check_health("remote-stale")["reason"] == "HEARTBEAT_STALE"


def test_invalid_modes_and_costs_are_rejected():
    with pytest.raises(ValueError, match="INVALID_EXECUTION_MODE"):
        ASICResource("bad", execution_mode="REAL")
    with pytest.raises(ValueError, match="INVALID_POWER_COST"):
        ASICResource("bad-cost", power_cost=-1)

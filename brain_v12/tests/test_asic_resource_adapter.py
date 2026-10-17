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


def test_register_simulator_fleet_uses_deterministic_ids_and_shared_config():
    brain = ASICResourceAdapter()
    fleet = brain.register_simulator_fleet(
        3, prefix="fleet", config={"hashrate": 2, "hashrate_unit": "TH", "power_watts": 1000}
    )
    assert [item["resource_id"] for item in fleet] == ["fleet-001", "fleet-002", "fleet-003"]
    assert all(item["execution_mode"] == "SIMULATOR" for item in fleet)
    assert all(item["verification_status"] == "SIMULATED" for item in fleet)
    assert len(brain.select({"asic.simulate"})) == 3


def test_register_simulator_fleet_rejects_unsafe_or_conflicting_config_before_registration():
    brain = ASICResourceAdapter()
    with pytest.raises(ValueError, match="FLEET_COUNT_OUT_OF_RANGE"):
        brain.register_simulator_fleet(0)
    with pytest.raises(ValueError, match="UNSUPPORTED_FLEET_CONFIG"):
        brain.register_simulator_fleet(2, config={"execution_mode": "PHYSICAL_DEVICE"})
    brain.register(ASICResource("fleet-001"))
    with pytest.raises(ValueError, match="FLEET_RESOURCE_ID_CONFLICT"):
        brain.register_simulator_fleet(2, prefix="fleet")
    assert list(brain.resources) == ["fleet-001"]

def test_asic_simulator_runs_bounded_sha256d_and_records_simulation_only_evidence():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("pow-sim"))
    header = bytes(80)
    result = brain.simulate_sha256d_pow(
        "pow-sim", header=header, target=(1 << 256) - 1,
        start_nonce=7, max_attempts=1,
    )
    assert result["result"]["software_hashes_performed"] == 1
    assert result["result"]["result"]["found"] is True
    assert result["result"]["result"]["nonce"] == 7
    assert result["result"]["software_hashing_performed"] is True
    assert result["result"]["rtl_executed"] is False
    assert result["result"]["physical_asic_executed"] is False
    assert result["result"]["pool_contacted"] is False
    assert result["result"]["share_submitted"] is False
    assert result["result"]["pool_acceptance_verified"] is False
    assert result["result"]["revenue_verified"] is False
    assert result["result"]["evidence_status"] == "SIMULATION_ONLY"
    assert result["evidence_verification"] == "VERIFIED"


def test_asic_sha256d_simulation_rejects_real_resource_modes_and_bad_header():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("remote-pow", execution_mode="REMOTE_PROVIDER"))
    with pytest.raises(PermissionError, match="SIMULATION_MODE_REQUIRED"):
        brain.simulate_sha256d_pow(
            "remote-pow", header=bytes(80), target=(1 << 256) - 1, max_attempts=1
        )
    brain.register(ASICResource("sim-bad"))
    with pytest.raises(ValueError, match="HEADER_MUST_BE_EXACTLY_80_BYTES"):
        brain.simulate_sha256d_pow(
            "sim-bad", header=b"bad", target=(1 << 256) - 1, max_attempts=1
        )



def test_rtl_self_test_requires_real_tool_result_and_persists_distinct_evidence(monkeypatch):
    import brain_v12.brain.asic_resource_adapter as module

    brain = ASICResourceAdapter()
    brain.register(ASICResource("rtl-sim"))
    monkeypatch.setattr(module, "run_sha256d_rtl_self_test", lambda **kwargs: {
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
    result = brain.simulate_sha256d_rtl("rtl-sim")
    assert result["task"]["status"] == "COMPLETED"
    assert result["result"]["execution_mode"] == "RTL_SIMULATION"
    assert result["evidence_verification"] == "VERIFIED"
    evidence = brain.evidence.get(result["evidence_ref"])
    assert evidence["kind"] == "asic_sha256d_rtl_simulation"


def test_rtl_self_test_failure_cannot_complete_task_or_create_success_evidence(monkeypatch):
    import brain_v12.brain.asic_resource_adapter as module

    brain = ASICResourceAdapter()
    brain.register(ASICResource("rtl-blocked"))
    monkeypatch.setattr(module, "run_sha256d_rtl_self_test", lambda **kwargs: {
        "contract_version": "brain.sha256d.execution.v1",
        "execution_mode": "RTL_SIMULATION",
        "status": "BLOCKED_TOOLCHAIN_UNAVAILABLE",
        "rtl_executed": False,
        "evidence_status": "BLOCKED",
    })
    result = brain.simulate_sha256d_rtl("rtl-blocked")
    assert result["task"]["status"] == "FAILED"
    assert result["evidence_ref"] is None
    assert result["evidence_verification"] == "NOT_VERIFIED"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"start_nonce": -1}, "START_NONCE_OUT_OF_RANGE"),
        ({"start_nonce": 0x1_0000_0000}, "START_NONCE_OUT_OF_RANGE"),
        ({"start_nonce": True}, "START_NONCE_OUT_OF_RANGE"),
        ({"max_attempts": 0}, "MAX_ATTEMPTS_MUST_BE_BETWEEN_1_AND_1000000"),
        ({"max_attempts": 1_000_001}, "MAX_ATTEMPTS_MUST_BE_BETWEEN_1_AND_1000000"),
        ({"max_attempts": True}, "MAX_ATTEMPTS_MUST_BE_BETWEEN_1_AND_1000000"),
        ({"target": -1}, "TARGET_MUST_BE_A_256_BIT_UNSIGNED_INTEGER"),
        ({"target": 1 << 256}, "TARGET_MUST_BE_A_256_BIT_UNSIGNED_INTEGER"),
    ],
)
def test_sha256d_simulation_rejects_nonce_target_and_attempt_bounds(kwargs, error):
    brain = ASICResourceAdapter()
    brain.register(ASICResource("bounds-sim"))
    args = {"header": bytes(80), "target": (1 << 256) - 1, "start_nonce": 0, "max_attempts": 1}
    args.update(kwargs)
    with pytest.raises(ValueError, match=error):
        brain.simulate_sha256d_pow("bounds-sim", **args)


def test_sha256d_simulation_accepts_last_uint32_nonce_without_wrapping_when_found():
    brain = ASICResourceAdapter()
    brain.register(ASICResource("last-nonce-sim"))
    result = brain.simulate_sha256d_pow(
        "last-nonce-sim", header=bytes(80), target=(1 << 256) - 1,
        start_nonce=0xFFFFFFFF, max_attempts=1,
    )
    assert result["result"]["result"]["found"] is True
    assert result["result"]["result"]["nonce"] == 0xFFFFFFFF
    assert result["result"]["software_hashes_performed"] == 1

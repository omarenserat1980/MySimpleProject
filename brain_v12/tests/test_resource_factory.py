from __future__ import annotations

import pytest

from brain_v12.brain.asic_resource_adapter import ASICResourceAdapter
from brain_v12.brain.profit_gate import ProfitGate
from brain_v12.brain.resource_factory import ResourceFactory


def test_factory_creates_n_simulators_without_per_node_code():
    factory = ResourceFactory()
    result = factory.create_asic_simulators(4, hashrate=250, hashrate_unit="GH", power_watts=100)
    assert result["count"] == 4
    assert [x["resource_id"] for x in result["resources"]] == [
        "ASIC-SIM-01", "ASIC-SIM-02", "ASIC-SIM-03", "ASIC-SIM-04"
    ]
    assert all(x["truth_level"] == "SIMULATED" for x in result["resources"])
    assert all(x["real_device"] is False and x["real_mining"] is False for x in result["resources"])
    assert all(x["revenue_verified"] is False and x["evidence_ref"] for x in result["resources"])


def test_factory_rejects_invalid_count_and_duplicate_ids_before_registration():
    factory = ResourceFactory()
    with pytest.raises(ValueError, match="SIMULATOR_COUNT_OUT_OF_RANGE"):
        factory.create_asic_simulators(0)
    factory.create_asic_simulators(2)
    before = set(factory.adapter.resources)
    with pytest.raises(ValueError, match="RESOURCE_ALREADY_REGISTERED"):
        factory.create_asic_simulators(3)
    assert set(factory.adapter.resources) == before


def test_simulation_work_result_is_repeatable_and_never_revenue():
    adapter = ASICResourceAdapter()
    factory = ResourceFactory(adapter)
    factory.create_asic_simulators(1, hashrate=12, hashrate_unit="GH")
    first = adapter.simulate("ASIC-SIM-01", duration_seconds=5)
    second = adapter.simulate("ASIC-SIM-01", duration_seconds=5)
    assert first["result"]["estimated_hashes"] == second["result"]["estimated_hashes"] == 60_000_000_000
    assert first["result"]["real_device_measurement"] is False
    assert first["result"]["revenue_verified"] is False


def test_reservation_prevents_conflicting_tasks_and_releases_on_completion():
    factory = ResourceFactory()
    factory.create_asic_simulators(1)
    assert factory.reserve("ASIC-SIM-01", "task-a")["status"] == "RESERVED"
    assert factory.reserve("ASIC-SIM-01", "task-b")["status"] == "RESOURCE_NOT_AVAILABLE"
    assert factory.begin("ASIC-SIM-01", "task-a")["status"] == "BUSY"
    assert factory.complete("ASIC-SIM-01", "task-a")["status"] == "COMPLETED"
    assert factory.reserve("ASIC-SIM-01", "task-b")["status"] == "RESOURCE_NOT_AVAILABLE"


def test_quarantine_blocks_work_and_recovery_requires_valid_registration_evidence():
    factory = ResourceFactory()
    factory.create_asic_simulators(1)
    failed = factory.fail_and_quarantine("ASIC-SIM-01", "synthetic failure")
    assert failed["status"] == "QUARANTINED"
    assert factory.reserve("ASIC-SIM-01", "task-a")["status"] == "BLOCKED_QUARANTINED"
    assert factory.recover("ASIC-SIM-01")["status"] == "AVAILABLE"
    assert factory.reserve("ASIC-SIM-01", "task-a")["status"] == "RESERVED"


def test_profit_gate_allows_only_verified_positive_economics():
    gate = ProfitGate()
    result = gate.evaluate(
        execution_mode="REMOTE_PROVIDER",
        truth_level="EXTERNALLY_VERIFIED",
        expected_revenue=20,
        costs={"electricity": 2, "pool_fees": 1, "hosting": 3, "network": 1, "other": 1},
        provider_verified=True,
        evidence_verified=True,
    )
    assert result["status"] == "PROFITABLE"
    assert result["allowed"] is True
    assert result["expected_net"] == 12


def test_profit_gate_blocks_loss_unknown_missing_cost_and_missing_revenue():
    gate = ProfitGate()
    base = {
        "execution_mode": "REMOTE_PROVIDER",
        "truth_level": "EXTERNALLY_VERIFIED",
        "expected_revenue": 5,
        "costs": {"electricity": 2, "pool_fees": 1, "hosting": 3, "network": 1, "other": 1},
        "provider_verified": True,
        "evidence_verified": True,
    }
    loss = gate.evaluate(**base)
    assert loss["status"] == "LOSS" and loss["allowed"] is False
    missing_cost = gate.evaluate(**{**base, "costs": {"electricity": 2}})
    assert missing_cost["status"] == "BLOCKED"
    assert any(reason.startswith("COST_MISSING_OR_INVALID:") for reason in missing_cost["reasons"])
    missing_revenue = gate.evaluate(**{**base, "expected_revenue": None})
    assert missing_revenue["status"] == "BLOCKED"
    assert "EXPECTED_REVENUE_MISSING_OR_INVALID" in missing_revenue["reasons"]


def test_profit_gate_blocks_simulation_and_unverified_provider():
    gate = ProfitGate()
    args = {
        "expected_revenue": 100,
        "costs": {"electricity": 0, "pool_fees": 0, "hosting": 0, "network": 0, "other": 0},
        "provider_verified": True,
        "evidence_verified": True,
    }
    simulated = gate.evaluate(**args, execution_mode="SIMULATOR", truth_level="SIMULATED")
    assert simulated["status"] == "BLOCKED"
    assert "SIMULATION_IS_NOT_REVENUE" in simulated["reasons"]
    unverified = gate.evaluate(**{**args, "provider_verified": False}, execution_mode="REMOTE_PROVIDER", truth_level="SELF_REPORTED")
    assert unverified["status"] == "BLOCKED"
    assert "PROVIDER_NOT_VERIFIED" in unverified["reasons"]


def test_economic_kill_switch_stops_on_loss_stale_or_unsafe():
    gate = ProfitGate()
    decision = {"status": "LOSS"}
    assert gate.kill_switch_required(decision)["stop"] is True
    assert gate.kill_switch_required({"status": "PROFITABLE"}, stale=True)["stop"] is True
    assert gate.kill_switch_required({"status": "PROFITABLE"}, unsafe=True)["stop"] is True
    assert gate.kill_switch_required({"status": "PROFITABLE"})["stop"] is False

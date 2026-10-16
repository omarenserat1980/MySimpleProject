from brain_v12.brain.brain_owned_mining_contract import (
    EXECUTION_TARGET,
    build_plan,
    classify_evidence,
    execution_gate,
)


def test_plan_assigns_computation_only_to_brain_runtime():
    plan = build_plan("sha256d", gateway_id="windows-omar-01")
    assert plan["execution_target"] == EXECUTION_TARGET
    assert plan["gateway"]["role"] == "connectivity_observation_only"
    assert plan["gateway"]["may_compute"] is False
    assert plan["physical_device_computation_allowed"] is False
    assert plan["external_miner_execution_allowed"] is False
    assert plan["execution_started"] is False
    assert plan["pool_contacted"] is False


def test_unknown_algorithm_is_rejected():
    import pytest
    with pytest.raises(ValueError, match="UNSUPPORTED_ALGORITHM"):
        build_plan("not-a-real-algorithm")


def test_execution_gate_fails_closed_without_native_backend():
    gate = execution_gate(
        backend_implemented=False,
        backend_attested=True,
        pool_endpoint_verified=True,
        credentials_in_secret_store=True,
        resource_budget_verified=True,
        explicit_user_approval=True,
    )
    assert gate["status"] == "BLOCKED"
    assert "BRAIN_OWNED_BACKEND_NOT_IMPLEMENTED" in gate["blockers"]
    assert gate["execution_allowed"] is False
    assert gate["execution_started"] is False


def test_complete_gate_is_only_ready_for_separate_review_not_execution():
    gate = execution_gate(
        backend_implemented=True,
        backend_attested=True,
        pool_endpoint_verified=True,
        credentials_in_secret_store=True,
        resource_budget_verified=True,
        explicit_user_approval=True,
    )
    assert gate["status"] == "READY_FOR_SEPARATE_EXECUTION_REVIEW"
    assert gate["execution_allowed"] is False
    assert gate["execution_started"] is False


def test_execution_gate_blocks_missing_backend_and_github_actions():
    gate = execution_gate(running_on_github_actions=True)
    assert gate["status"] == "BLOCKED"
    assert "BRAIN_OWNED_BACKEND_NOT_IMPLEMENTED" in gate["blockers"]
    assert "GITHUB_ACTIONS_MINING_FORBIDDEN" in gate["blockers"]
    assert gate["execution_allowed"] is False


def test_simulation_never_counts_as_real_mining():
    result = classify_evidence({"simulation": True, "hashrate_hs": 100, "accepted_shares": 10})
    assert result["status"] == "SIMULATION_ONLY"
    assert result["counts_as_real_mining"] is False


def test_external_hardware_mining_evidence_is_rejected():
    result = classify_evidence({
        "source": "pool_api",
        "worker_id": "external-worker",
        "hashrate_hs": 1000,
        "accepted_shares": 5,
        "pool_source_verified": True,
        "brain_runtime_attested": True,
        "compute_host": "physical_asic",
        "physical_device_computation": True,
        "external_miner_execution": True,
    })
    assert result["counts_as_real_mining"] is False
    assert result["revenue_verified"] is False


def test_verified_pool_evidence_requires_brain_runtime_provenance():
    result = classify_evidence({
        "source": "pool_api",
        "worker_id": "brain-worker-01",
        "hashrate_hs": 1000,
        "accepted_shares": 5,
        "pool_source_verified": True,
        "brain_runtime_attested": True,
        "compute_host": EXECUTION_TARGET,
        "physical_device_computation": False,
        "external_miner_execution": False,
    })
    assert result["status"] == "BRAIN_RUNTIME_POOL_ACTIVITY_VERIFIED"
    assert result["counts_as_real_mining"] is True
    assert result["revenue_verified"] is False

from brain_v12.brain.mining_node_api import (
    classify_real_mining_evidence,
    get_software_only_contract,
    node_status,
    readiness_status,
)


def test_node_status_declares_gateway_only_software_execution():
    status = node_status()
    assert status["execution_mode"] == "BRAIN_OWNED_SOFTWARE_ONLY_PLAN_ONLY"
    assert status["physical_devices_role"] == "CONNECTIVITY_OBSERVATION_ONLY"
    assert status["native_pow_primitive"] == "IMPLEMENTED_SHA256D_BOUNDED"
    assert status["native_mining_backend"] == "NOT_IMPLEMENTED"
    assert status["external_miner_execution"] == "FORBIDDEN"
    assert status["local_device_computation_allowed"] is False
    assert status["real_mining_claim"] is False


def test_readiness_blocks_real_mining_on_missing_brain_backend_not_missing_device():
    status = readiness_status()
    assert status["real_mining_ready"] is False
    assert status["gates"]["G1a_sha256d_pow_primitive"] == "READY_BOUNDED_LIBRARY_ONLY"
    assert status["gates"]["G2_brain_owned_compute_backend"] == "BLOCKED_NOT_IMPLEMENTED"
    assert status["gates"]["G4_gateway_connectivity"] == "NOT_REQUIRED_FOR_COMPUTE"
    assert any("native mining compute backend is not implemented" in item.lower() for item in status["blockers"])


def test_api_contract_endpoint_is_plan_only_and_fail_closed():
    result = get_software_only_contract()
    assert result["plan"]["physical_device_computation_allowed"] is False
    assert result["plan"]["external_miner_execution_allowed"] is False
    assert result["execution_gate"]["execution_allowed"] is False
    assert result["execution_started"] is False


def test_caller_supplied_evidence_never_promotes_real_mining():
    claimed = {
        key: {"verified": True, "source": "caller", "digest": "not-a-trusted-digest"}
        for key in (
            "authenticated_host_attestation",
            "authenticated_brain_connection",
            "pool_session_attestation",
            "accepted_share_attestation",
        )
    }
    result = classify_real_mining_evidence(claimed)
    assert result["real_mining_verified"] is False
    assert result["state"] == "REQUIRES_INDEPENDENT_SERVER_VERIFICATION"

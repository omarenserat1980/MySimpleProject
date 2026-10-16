from brain_v12.brain.mining_node_api import (
    classify_real_mining_evidence,
    node_status,
    readiness_status,
)


def test_status_is_explicitly_simulated_and_makes_no_real_claims():
    result = node_status()
    assert result["node_mode"] == "SIMULATOR"
    assert result["state"] == "SIMULATED"
    assert result["real_mining_claim"] is False
    assert result["revenue_claim"] is False
    assert result["network_access_performed"] is False
    assert result["hardware_access_performed"] is False
    assert {
        "brain_supervisor",
        "asic_simulator",
        "bitcoin_mining_intelligence",
        "brain_owned_mining_contract",
        "brain_owned_compute_backend_pending",
    }.issubset(set(result["integrated_components"]))
    assert result["execution_mode"] == "BRAIN_OWNED_SOFTWARE_ONLY_PLAN_ONLY"
    assert result["physical_devices_role"] == "CONNECTIVITY_OBSERVATION_ONLY"
    assert result["external_miner_execution"] == "FORBIDDEN"
    assert result["local_device_computation_allowed"] is False


def test_readiness_keeps_real_mining_blocked_without_trusted_collectors():
    result = readiness_status()
    assert result["software_api_ready"] is True
    assert result["real_mining_ready"] is False
    assert result["state"] == "BLOCKED"
    assert result["gates"]["G2_brain_owned_compute_backend"] == "BLOCKED_LIVE_BACKEND_NOT_IMPLEMENTED"
    assert result["gates"]["G2a_bounded_sha256d_primitive"] == "READY_BOUNDED_LIBRARY_ONLY"
    assert result["gates"]["G2b_live_compute_host_attestation"] == "BLOCKED_HOST_ATTESTATION_REQUIRED"
    assert result["gates"]["G2c_pool_share_submission_adapter"] == "BLOCKED_NOT_IMPLEMENTED"
    assert result["gates"]["G4_gateway_connectivity"] == "NOT_REQUIRED_FOR_COMPUTE"
    assert result["gates"]["G5_pool_shares"].startswith("BLOCKED")
    assert result["real_mining_claim"] is False
    assert result["revenue_claim"] is False


def test_empty_or_malformed_evidence_fails_closed():
    for evidence in (None, [], {}, {"accepted_share_attestation": True}):
        result = classify_real_mining_evidence(evidence)
        assert result["real_mining_verified"] is False
        assert result["state"] == "BLOCKED"
        assert len(result["missing_evidence"]) == 4


def test_caller_supplied_fields_cannot_promote_mining_to_verified():
    evidence = {
        key: {"verified": True, "source": "user-input", "digest": "not-a-trusted-attestation"}
        for key in (
            "authenticated_host_attestation",
            "authenticated_brain_connection",
            "pool_session_attestation",
            "accepted_share_attestation",
        )
    }
    result = classify_real_mining_evidence(evidence)
    assert result["real_mining_verified"] is False
    assert result["state"] == "REQUIRES_INDEPENDENT_SERVER_VERIFICATION"
    assert result["missing_evidence"] == []



def test_software_only_contract_endpoint_fails_closed():
    from brain_v12.brain.mining_node_api import get_software_only_contract

    result = get_software_only_contract()
    assert result["plan"]["physical_device_computation_allowed"] is False
    assert result["plan"]["external_miner_execution_allowed"] is False
    assert result["execution_gate"]["execution_allowed"] is False
    assert result["execution_started"] is False

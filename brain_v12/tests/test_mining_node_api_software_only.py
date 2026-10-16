from brain_v12.brain.mining_node_api import (
    classify_real_mining_evidence,
    compute_backend_preflight,
    pool_evidence_status,
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
    assert status["bounded_software_compute_primitive"] == "AVAILABLE_SHA256D_LIBRARY"
    assert status["live_compute_ready"] is False
    assert status["external_miner_execution"] == "FORBIDDEN"
    assert status["local_device_computation_allowed"] is False
    assert status["real_mining_claim"] is False


def test_readiness_blocks_real_mining_on_missing_brain_backend_not_missing_device():
    status = readiness_status()
    assert status["real_mining_ready"] is False
    assert status["gates"]["G1a_sha256d_pow_primitive"] == "READY_BOUNDED_LIBRARY_ONLY"
    assert status["gates"]["G2_brain_owned_compute_backend"] == "BLOCKED_LIVE_BACKEND_NOT_IMPLEMENTED"
    assert status["gates"]["G2a_bounded_sha256d_primitive"] == "READY_BOUNDED_LIBRARY_ONLY"
    assert status["gates"]["G2b_live_compute_host_attestation"] == "BLOCKED_HOST_ATTESTATION_REQUIRED"
    assert status["gates"]["G2c_pool_share_submission_adapter"] == "BLOCKED_NOT_IMPLEMENTED"
    assert status["gates"]["G4_gateway_connectivity"] == "NOT_REQUIRED_FOR_COMPUTE"
    assert any("production brain-owned compute service is not implemented" in item.lower() for item in status["blockers"])


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


def test_compute_preflight_only_runs_known_answer_hash_and_keeps_live_gate_closed():
    result = compute_backend_preflight()
    assert result["known_answer_test_passed"] is True
    assert result["nonce_search_executed"] is False
    assert result["pool_contacted"] is False
    assert result["network_access_performed"] is False
    assert result["execution_allowed"] is False
    assert result["execution_started"] is False
    assert result["live_execution_gate"]["status"] == "BLOCKED"


def test_pool_evidence_status_is_read_only_and_does_not_claim_pool_activity():
    result = pool_evidence_status()
    assert result["http_method"] == "GET"
    assert result["pool_query_performed"] is False
    assert result["network_access_performed"] is False
    assert result["pool_activity_verified"] is False
    assert result["accepted_share_submission_verified"] is False
    assert result["brain_runtime_activity_verified"] is False
    assert result["payout_verified"] is False
    assert result["revenue_verified"] is False
    assert result["execution_allowed"] is False

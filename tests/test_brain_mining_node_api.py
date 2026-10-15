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
        "bitcoin_worker",
    }.issubset(set(result["integrated_components"]))


def test_readiness_keeps_real_mining_blocked_without_trusted_collectors():
    result = readiness_status()
    assert result["software_api_ready"] is True
    assert result["real_mining_ready"] is False
    assert result["state"] == "BLOCKED"
    assert result["gates"]["G4_physical_device"].startswith("BLOCKED")
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

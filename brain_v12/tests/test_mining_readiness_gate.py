from brain_v12.brain.mining_readiness_gate import evaluate_mining_readiness


def test_missing_evidence_fails_closed():
    result = evaluate_mining_readiness()
    assert result["state"] == "BLOCKED"
    assert "ASIC_READ_ONLY_DEVICE_EVIDENCE_MISSING" in result["blockers"]
    assert result["readiness_for_real_mining"] is False
    assert result["revenue_realized"] is False


def test_pool_wide_stats_and_subscribe_do_not_prove_local_mining():
    result = evaluate_mining_readiness(ckpool_evidence={
        "pool_telemetry": {"pool_stats_available": True, "local_share_acceptance_verified": False},
        "stratum_probe": {"tcp_connected": True, "subscription_response_present": True},
        "block_found_verified": False,
        "payout_verified": False,
    })
    assert "LOCAL_HASHRATE_NOT_VERIFIED" in result["blockers"]
    assert "ACCEPTED_SHARES_NOT_VERIFIED" in result["blockers"]
    assert "BLOCK_REWARD_NOT_VERIFIED" in result["blockers"]
    assert result["revenue_realized"] is False


def test_asic_telemetry_alone_does_not_prove_accepted_shares_or_payout():
    result = evaluate_mining_readiness(
        asic_status={"state": "READ_ONLY_DATA_RECEIVED", "device_contacted": True,
                     "telemetry": {"reported_hashrate": 123, "reported_hashrate_unit": "GH/s"}},
        ckpool_evidence={"stratum_probe": {"tcp_connected": True, "subscription_response_present": True}},
        payout_address_configured=True,
    )
    assert "ACCEPTED_SHARES_NOT_VERIFIED" in result["blockers"]
    assert "PAYOUT_NOT_VERIFIED" in result["blockers"]
    assert result["real_mining_verified"] is False


def test_gate_never_performs_side_effects():
    result = evaluate_mining_readiness()
    assert all(value is False for value in result["side_effects"].values())

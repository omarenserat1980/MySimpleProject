from brain_v12.brain.asic_hosting_evidence import assess_asic_evidence


def test_empty_evidence_fails_closed():
    result = assess_asic_evidence({})
    assert result["stage"] == "BLOCKED"
    assert result["claim_verified"] is False
    assert result["automatic_activation_allowed"] is False


def test_device_identity_is_not_mining_proof():
    result = assess_asic_evidence({
        "provider_legal_name": "Example Hosting Ltd",
        "device_model": "ASIC model",
        "device_serial_or_provider_asset_id": "asset-123",
        "physical_asic_confirmed": True,
        "facility_evidence_url": "https://example.com/facility",
    })
    assert result["stage"] == "DEVICE_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION"
    assert result["claim_verified"] is False
    assert "POOL_EVIDENCE_URL_INVALID" in result["evidence_errors"]


def test_pool_metrics_and_payout_are_separate_claims():
    base = {
        "provider_legal_name": "Example Hosting Ltd",
        "device_model": "ASIC model",
        "device_serial_or_provider_asset_id": "asset-123",
        "physical_asic_confirmed": True,
        "facility_evidence_url": "https://example.com/facility",
        "pool_dashboard_url": "https://pool.example.com/account",
        "observed_hashrate_ths": 100,
        "accepted_shares": 12,
    }
    mining = assess_asic_evidence(base)
    assert mining["stage"] == "MINING_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION"
    assert "MATCHABLE_PAYOUT_EVIDENCE_MISSING" in mining["evidence_errors"]

    paid = assess_asic_evidence({
        **base,
        "payout_transaction_id": "example-tx-id",
        "payout_amount_btc": 0.0001,
    })
    assert paid["stage"] == "PAYOUT_CLAIM_REQUIRES_INDEPENDENT_VERIFICATION"
    assert paid["claim_verified"] is False
    assert paid["automatic_activation_allowed"] is False


def test_non_https_facility_is_rejected():
    result = assess_asic_evidence({
        "provider_legal_name": "Example Hosting Ltd",
        "device_model": "ASIC model",
        "device_serial_or_provider_asset_id": "asset-123",
        "physical_asic_confirmed": True,
        "facility_evidence_url": "http://example.com/facility",
    })
    assert result["stage"] == "BLOCKED"
    assert "FACILITY_EVIDENCE_URL_INVALID" in result["evidence_errors"]

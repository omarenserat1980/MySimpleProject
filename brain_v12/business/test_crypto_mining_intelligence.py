from brain_v12.business.crypto_mining_intelligence import (
    MiningMachine, NetworkSnapshot, PayoutEvidence, analyze_mining,
    build_intelligence_report, verify_payout,
)


def test_profitable_case_is_human_approval():
    machine = MiningMachine("test-asic", 200, 15, hardware_cost_usd=5000, pool_fee_pct=2)
    network = NetworkSnapshot("BTC", 0.04, "2026-10-02T00:00:00Z", "test",
                              evidence_urls=("https://example.test/hashprice",))
    result = analyze_mining(machine, network, 0.05)
    assert result.net_daily_profit_usd > 0
    assert result.status == "HUMAN_APPROVAL"
    assert result.break_even_electricity_usd_kwh > 0


def test_loss_case_is_wait():
    machine = MiningMachine("test-asic", 200, 30)
    network = NetworkSnapshot("BTC", 0.03, "2026-10-02T00:00:00Z", "test")
    result = analyze_mining(machine, network, 0.10)
    assert result.net_daily_profit_usd < 0
    assert result.status == "WAIT"


def test_report_has_no_external_action_capability():
    machine = MiningMachine("test", 100, 20)
    network = NetworkSnapshot("BTC", 0.04, "2026-10-02", "test")
    report = build_intelligence_report(machine, network, 0.05, [0.03, 0.05, 0.10])
    assert report["guardrails"]["trading_enabled"] is False
    assert report["guardrails"]["purchase_enabled"] is False
    assert report["analysis"]["assumptions"]["result_class"] == "EXPECTED_ONLY"
    assert len(report["electricity_sensitivity"]) == 3


def test_payout_without_txid_cannot_be_realized():
    evidence = PayoutEvidence(
        provider="CloudMineCrypto",
        observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=0.00000020,
        withdrawal_requested_btc=0.00000010,
        network="lightning",
        destination_fingerprint="wallet:sha256:abc",
        received_btc=0.0,
    )
    result = verify_payout(evidence)
    assert result["status"] == "PENDING_WITHDRAWAL_EVIDENCE"
    assert result["financial_state"] == "EXPECTED"


def test_payout_with_chain_evidence_is_realized():
    evidence = PayoutEvidence(
        provider="CloudMineCrypto",
        observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=0.00000120,
        withdrawal_requested_btc=0.00000100,
        network="bitcoin",
        destination_fingerprint="wallet:sha256:abc",
        txid="abc123",
        explorer_url="https://example.test/tx/abc123",
        received_btc=0.00000095,
        fee_btc=0.00000005,
    )
    result = verify_payout(evidence)
    assert result["status"] == "VERIFIED_COMPLETED"
    assert result["financial_state"] == "REVENUE_REALIZED"
    assert result["checks"]["on_chain_proof"] is True


def test_tampered_evidence_is_rejected():
    evidence = PayoutEvidence(
        provider="CloudMineCrypto",
        observed_at="2026-10-02T23:30:00+03:00",
        balance_btc=1.0,
        withdrawal_requested_btc=0.5,
        network="bitcoin",
        destination_fingerprint="wallet:sha256:abc",
        txid="abc123",
        explorer_url="https://example.test/tx/abc123",
        received_btc=0.49,
        evidence_sha256="tampered",
    )
    result = verify_payout(evidence)
    assert result["status"] == "REJECTED_EVIDENCE_INTEGRITY"
    assert result["financial_state"] == "UNVERIFIED"

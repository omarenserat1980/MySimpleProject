from brain_v12.business.crypto_mining_intelligence import (
    MiningMachine, NetworkSnapshot, analyze_mining, build_intelligence_report
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

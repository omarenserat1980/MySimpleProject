from brain_v12.business.mining_opportunity_audit_bridge import (
    build_mining_opportunity_audit_record,
)
from brain_v12.business.mining_opportunity_intelligence import (
    build_mining_opportunity_report,
)
from brain_v12.business.crypto_market_snapshot import MarketSnapshot


def _report():
    payload = {"btc": {"workers": {
        "account.worker1": {
            "state": "ok",
            "last_share": 1542103204,
            "hash_rate_5m": 14977000000000,
            "hash_rate_60m": 15302000000000,
            "hash_rate_24h": 15351000000000,
            "shares_5m": 90304,
            "shares_60m": 1125762,
            "shares_24h": 20945364,
        }
    }}}
    market = MarketSnapshot(
        asset="BTC",
        hashprice_usd_per_th_day=0.04,
        observed_at="2026-10-03T04:00:00+00:00",
        source="test:market",
        btc_price_usd=100000,
        network_hashrate_eh=900,
        difficulty=1,
        evidence_urls=("test:market",),
    )
    return build_mining_opportunity_report(
        braiins_payload=payload,
        market=market,
        electricity_usd_kwh=0.05,
        efficiency_j_th=15,
    )


def test_audit_bridge_is_analysis_only():
    record = build_mining_opportunity_audit_record(
        _report(), opportunity_id="mining-worker-account.worker1"
    )
    assert record["record_type"] == "MINING_OPPORTUNITY_ANALYSIS"
    assert record["status"] == "ANALYSIS_ONLY"
    assert record["analysis_only"] is True
    assert record["decision_policy"]["read_only"] is True
    assert record["decision_policy"]["revenue_realized"] is False
    assert record["decision_policy"]["funds_moved_by_brain"] is False


def test_audit_bridge_rejects_non_read_only_reports():
    report = _report()
    report["decision_policy"]["read_only"] = False
    try:
        build_mining_opportunity_audit_record(
            report, opportunity_id="test"
        )
    except ValueError:
        return
    raise AssertionError("non-read-only report must be rejected")

from brain_v12.business.braiins_readonly_adapter import parse_braiins_workers_response
from brain_v12.business.crypto_market_snapshot import MarketSnapshot
from brain_v12.business.mining_opportunity_intelligence import (
    build_mining_opportunity_report,
)


def market():
    return MarketSnapshot(
        asset="BTC",
        hashprice_usd_per_th_day=0.04,
        observed_at="2026-10-03T04:00:00+00:00",
        source="test:market",
        btc_price_usd=100000,
        network_hashrate_eh=900,
        difficulty=1,
        evidence_urls=("test:market",),
    )


def payload():
    return {"btc": {"workers": {
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


def test_opportunity_combines_worker_market_and_economics():
    report = build_mining_opportunity_report(
        braiins_payload=payload(),
        market=market(),
        electricity_usd_kwh=0.05,
        efficiency_j_th=15,
    )
    assert report["engine"] == "Brain Mining Opportunity Intelligence"
    assert len(report["workers"]) == 1
    worker = report["workers"][0]
    assert worker["worker_id"] == "account.worker1"
    assert worker["economics"]["base"]["status"] == "ECONOMICALLY_PLAUSIBLE"


def test_opportunity_is_read_only():
    report = build_mining_opportunity_report(
        braiins_payload=payload(),
        market=market(),
        electricity_usd_kwh=0.05,
        efficiency_j_th=15,
    )
    policy = report["decision_policy"]
    assert policy["read_only"] is True
    assert policy["auto_purchase"] is False
    assert policy["auto_contract"] is False
    assert policy["auto_withdrawal"] is False
    assert policy["funds_moved_by_brain"] is False
    assert policy["revenue_realized"] is False

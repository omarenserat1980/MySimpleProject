from brain_v12.business.mining_economics_engine import (
    build_mining_economics_engine_report,
)
from brain_v12.business.mining_economics_gate import MiningEconomicsInput


def base(**overrides):
    values = dict(
        hashrate_th=200,
        hashprice_usd_per_th_day=0.04,
        electricity_usd_kwh=0.05,
        efficiency_j_th=15,
        uptime_pct=95,
        pool_fee_pct=2.5,
        market_source="mempool+btc-price",
    )
    values.update(overrides)
    return MiningEconomicsInput(**values)


def test_engine_contains_base_and_sensitivity():
    report = build_mining_economics_engine_report(
        base(),
        electricity_scenarios=[0.04, 0.05, 0.08],
        hashprice_multipliers=[0.5, 1.0, 1.5],
    )
    assert report["engine"] == "Brain Mining Economics Engine"
    assert len(report["sensitivity"]["electricity"]) == 3
    assert len(report["sensitivity"]["hashprice"]) == 3
    assert report["base"]["status"] == "ECONOMICALLY_PLAUSIBLE"


def test_engine_is_analysis_only():
    report = build_mining_economics_engine_report(base())
    policy = report["decision_policy"]
    assert policy["analysis_only"] is True
    assert policy["auto_purchase"] is False
    assert policy["auto_contract"] is False
    assert policy["auto_withdrawal"] is False
    assert policy["funds_moved_by_brain"] is False
    assert policy["revenue_realized"] is False


def test_engine_rejects_invalid_scenarios():
    try:
        build_mining_economics_engine_report(base(), electricity_scenarios=[-0.01])
    except ValueError:
        pass
    else:
        raise AssertionError("negative electricity scenario must be rejected")

    try:
        build_mining_economics_engine_report(base(), hashprice_multipliers=[0])
    except ValueError:
        pass
    else:
        raise AssertionError("non-positive hashprice multiplier must be rejected")

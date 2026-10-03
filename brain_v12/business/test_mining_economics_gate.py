from brain_v12.business.mining_economics_gate import (
    MiningEconomicsInput, evaluate_mining_economics,
)


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


def test_positive_case_is_plausible_not_guaranteed():
    result = evaluate_mining_economics(base())
    assert result["status"] == "ECONOMICALLY_PLAUSIBLE"
    assert result["net_daily_cashflow_usd"] > 0
    assert result["guardrails"]["auto_purchase"] is False


def test_negative_case_is_not_economic():
    result = evaluate_mining_economics(base(electricity_usd_kwh=0.15))
    assert result["status"] == "NOT_ECONOMIC"
    assert result["net_daily_cashflow_usd"] < 0


def test_stale_market_is_uncertain():
    result = evaluate_mining_economics(base(observation_age_hours=25))
    assert result["status"] == "UNCERTAIN"


def test_missing_source_is_uncertain():
    result = evaluate_mining_economics(base(market_source=""))
    assert result["status"] == "UNCERTAIN"


def test_invalid_input_rejected():
    try:
        evaluate_mining_economics(base(hashrate_th=0))
    except ValueError:
        return
    raise AssertionError("invalid input must be rejected")

from brain_v12.brain.bitcoin_solo_economics import estimate_solo_block_interval_seconds


def test_estimate_is_transparent_and_never_recognizes_revenue():
    result = estimate_solo_block_interval_seconds(300_000, 202e15)
    assert result["valid"] is True
    assert result["device_share_of_network_hashrate"] < 1e-9
    assert result["idealized_mean_time_to_find_one_block_years"] > 1_000_000
    assert result["revenue_realized"] is False
    assert result["payout_forecast_is_guaranteed"] is False


def test_invalid_hashrates_fail_closed():
    for local, network in [(0, 100), (-1, 100), (1, 0), (float('nan'), 100)]:
        assert estimate_solo_block_interval_seconds(local, network)["valid"] is False

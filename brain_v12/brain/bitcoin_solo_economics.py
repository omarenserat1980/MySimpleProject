"""Transparent back-of-envelope Bitcoin solo-mining feasibility calculations.

Pure arithmetic only. No network calls, miner execution, or income recognition.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "electronic-brain.bitcoin-solo-economics.v1"


def estimate_solo_block_interval_seconds(device_hashrate_hs: float, network_hashrate_hs: float,
                                         target_block_interval_seconds: float = 600.0) -> dict[str, Any]:
    """Estimate mean block interval under idealized constant-rate assumptions."""
    try:
        local = float(device_hashrate_hs)
        network = float(network_hashrate_hs)
        block_interval = float(target_block_interval_seconds)
    except (TypeError, ValueError):
        return {"schema": SCHEMA, "valid": False, "error": "NON_NUMERIC_INPUT"}
    if not all(map(lambda x: x == x and abs(x) != float("inf"), (local, network, block_interval))):
        return {"schema": SCHEMA, "valid": False, "error": "NON_FINITE_INPUT"}
    if local <= 0 or network <= 0 or block_interval <= 0:
        return {"schema": SCHEMA, "valid": False, "error": "INPUTS_MUST_BE_POSITIVE"}
    expected_seconds = (network / local) * block_interval
    return {
        "schema": SCHEMA,
        "valid": True,
        "device_hashrate_hs": local,
        "network_hashrate_hs": network,
        "assumed_network_block_interval_seconds": block_interval,
        "device_share_of_network_hashrate": local / network,
        "idealized_mean_time_to_find_one_block_seconds": expected_seconds,
        "idealized_mean_time_to_find_one_block_years": expected_seconds / (365.25 * 24 * 3600),
        "revenue_realized": False,
        "payout_forecast_is_guaranteed": False,
        "limitations": [
            "Expected value only, not a prediction of when a block will be found.",
            "Assumes constant device and network hashrate and a 600-second mean block interval.",
            "Does not account for pool rules, downtime, stale work, fees, hardware power, or thermal throttling.",
            "A CPU SHA256d benchmark is not proof of a production miner or accepted shares.",
        ],
    }

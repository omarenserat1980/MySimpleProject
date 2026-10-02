"""Fetch free public BTC mining-market data with fail-closed validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

MEMPOOL_PRICES = "https://mempool.space/api/v1/prices"
MEMPOOL_HASHRATE = "https://mempool.space/api/v1/mining/hashrate/1w"
HASHPRICE_URL = "https://d-central.tech/wp-json/dc/v1/hashprice"


def _get_json(url: str, timeout: int = 15):
    req = Request(url, headers={"User-Agent": "ElectronicBrain-CryptoMiningIntelligence/1.0"})
    with urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise RuntimeError(f"{url} HTTP {r.status}")
        return json.loads(r.read().decode("utf-8"))


def _positive_number(value, name):
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{name} is missing or invalid")
    return float(value)


def collect_btc_market_snapshot() -> dict:
    observed_at = datetime.now(timezone.utc).isoformat()
    prices = _get_json(MEMPOOL_PRICES)
    mining = _get_json(MEMPOOL_HASHRATE)

    if not isinstance(prices, dict):
        raise ValueError("mempool price payload is not an object")
    if not isinstance(mining, list) or not mining:
        raise ValueError("mempool hashrate payload is empty")

    usd = _positive_number(prices.get("USD"), "BTC USD price")
    latest = mining[-1] if isinstance(mining[-1], dict) else None
    if not latest:
        raise ValueError("mempool hashrate record is invalid")

    hashrate = _positive_number(latest.get("avgHashrate"), "network hashrate")
    difficulty = _positive_number(latest.get("difficulty"), "network difficulty")

    hp_payload = _get_json(HASHPRICE_URL)
    if not isinstance(hp_payload, dict):
        raise ValueError("hashprice payload is not an object")
    candidates = (
        hp_payload.get("usd_per_th_day"),
        hp_payload.get("hashprice_usd_per_th_day"),
        hp_payload.get("hashprice", {}).get("usd_per_th_day")
        if isinstance(hp_payload.get("hashprice"), dict) else None,
    )
    hashprice = next((x for x in candidates if isinstance(x, (int, float)) and x > 0), None)
    if hashprice is None:
        raise ValueError("hashprice field not found")

    return {
        "asset": "BTC",
        "observed_at": observed_at,
        "sources": {
            "price": MEMPOOL_PRICES,
            "network": MEMPOOL_HASHRATE,
            "hashprice": HASHPRICE_URL,
        },
        "btc_price_usd": usd,
        "network_hashrate_eh_s": hashrate / 1e18,
        "difficulty": difficulty,
        "hashprice_usd_per_th_day": float(hashprice),
        "data_quality": "FRESH",
        "external_actions_enabled": False,
    }

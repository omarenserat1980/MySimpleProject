"""Fetch free public BTC mining-market data with fail-closed validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

MEMPOOL_PRICES = "https://mempool.space/api/v1/prices"
MEMPOOL_HASHRATE_ENDPOINTS = (
    "https://mempool.space/api/v1/mining/hashrate/1w",
    "https://mempool.space/api/v1/mining/hashrate/3d",
    "https://mempool.space/api/v1/mining/hashrate/24h",
)
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
    mining = None
    network_source = None
    for endpoint in MEMPOOL_HASHRATE_ENDPOINTS:
        try:
            candidate = _get_json(endpoint)
        except Exception:
            continue
        if isinstance(candidate, list) and candidate:
            mining = candidate
            network_source = endpoint
            break

    if not isinstance(prices, dict):
        raise ValueError("mempool price payload is not an object")
    if not isinstance(mining, list) or not mining or not network_source:
        raise ValueError("mempool hashrate payload is empty across all supported periods")

    usd = _positive_number(prices.get("USD"), "BTC USD price")
    latest = mining[-1] if isinstance(mining[-1], dict) else None
    if not latest:
        raise ValueError("mempool hashrate record is invalid")

    hashrate = _positive_number(latest.get("avgHashrate"), "network hashrate")
    difficulty = _positive_number(latest.get("difficulty"), "network difficulty")

    hashprice = None
    hashprice_source = HASHPRICE_URL
    try:
        hp_payload = _get_json(HASHPRICE_URL)
        if isinstance(hp_payload, dict):
            candidates = (
                hp_payload.get("usd_per_th_day"),
                hp_payload.get("hashprice_usd_per_th_day"),
                hp_payload.get("hashprice", {}).get("usd_per_th_day")
                if isinstance(hp_payload.get("hashprice"), dict) else None,
            )
            hashprice = next((x for x in candidates if isinstance(x, (int, float)) and x > 0), None)
    except Exception:
        hashprice = None

    if hashprice is None:
        # Conservative, source-independent fallback: derive gross BTC block subsidy
        # revenue per TH/day from the fresh Mempool network hashrate and BTC price.
        # This is a modelled estimate, not proof of mining revenue.
        block_subsidy_btc = 3.125
        network_th_s = hashrate / 1e12
        hashprice = (144.0 * block_subsidy_btc * usd) / network_th_s
        hashprice_source = "derived:mempool-network-hashrate+btc-price:block-subsidy-only"

    return {
        "asset": "BTC",
        "observed_at": observed_at,
        "sources": {
            "price": MEMPOOL_PRICES,
            "network": network_source,
            "hashprice": hashprice_source,
        },
        "btc_price_usd": usd,
        "network_hashrate_eh_s": hashrate / 1e18,
        "difficulty": difficulty,
        "hashprice_usd_per_th_day": float(hashprice),
        "data_quality": "FRESH",
        "external_actions_enabled": False,
    }


def collect_validated_btc_market_snapshot(max_age_hours: float = 24.0) -> dict:
    """Collect public data and enforce the canonical freshness contract."""
    from .crypto_market_snapshot import MarketSnapshot

    payload = collect_btc_market_snapshot()
    snapshot = MarketSnapshot(
        asset=payload["asset"],
        hashprice_usd_per_th_day=payload["hashprice_usd_per_th_day"],
        observed_at=payload["observed_at"],
        source=payload["sources"]["hashprice"],
        btc_price_usd=payload["btc_price_usd"],
        network_hashrate_eh=payload["network_hashrate_eh_s"],
        difficulty=payload["difficulty"],
        evidence_urls=tuple(payload["sources"].values()),
    )
    validation = snapshot.validate(max_age_hours=max_age_hours)
    return {**payload, "freshness_validation": validation}

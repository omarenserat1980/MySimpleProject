"""Free public mining-data adapter with fail-closed behavior."""
from __future__ import annotations

import json
from urllib.request import Request, urlopen

D_CENTRAL_HASHPRICE_URL = "https://d-central.tech/wp-json/dc/v1/hashprice"


def fetch_bitcoin_hashprice(timeout_seconds: int = 10) -> dict:
    request = Request(
        D_CENTRAL_HASHPRICE_URL,
        headers={"User-Agent": "ElectronicBrain-CryptoMiningIntelligence/1.0"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"hashprice source HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("hashprice source returned a non-object payload")

    # The public endpoint can evolve; require an explicit numeric hashprice.
    candidates = (
        payload.get("usd_per_th_day"),
        payload.get("hashprice_usd_per_th_day"),
        payload.get("hashprice", {}).get("usd_per_th_day")
        if isinstance(payload.get("hashprice"), dict) else None,
    )
    value = next((x for x in candidates if isinstance(x, (int, float)) and x > 0), None)
    if value is None:
        raise ValueError("hashprice field not found in source payload")

    return {
        "asset": "BTC",
        "hashprice_usd_per_th_day": float(value),
        "source": D_CENTRAL_HASHPRICE_URL,
        "raw": payload,
    }

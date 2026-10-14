"""Read-only Bitcoin mainnet transaction evidence collector.

Fetches a transaction and current tip height from the public mempool.space API.
It never reads pool credentials, starts mining, signs transactions, or moves funds.
This supplies chain-side evidence only; pool-side payout evidence is still required.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.request import Request, urlopen

BASE_URL = "https://mempool.space/api"


def _get_json(url: str, timeout: int = 15):
    request = Request(url, headers={"User-Agent": "ElectronicBrain-BitcoinEvidence/1.0"})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"Bitcoin explorer returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def collect_bitcoin_chain_transaction(txid: str) -> dict:
    """Return normalized mainnet transaction data, or fail closed on invalid data."""
    normalized_txid = str(txid or "").strip().lower()
    if len(normalized_txid) != 64 or any(ch not in "0123456789abcdef" for ch in normalized_txid):
        raise ValueError("txid must be a 64-character hexadecimal transaction ID")

    transaction = _get_json(f"{BASE_URL}/tx/{normalized_txid}")
    if not isinstance(transaction, dict) or transaction.get("txid", "").lower() != normalized_txid:
        raise ValueError("explorer transaction response does not match requested txid")
    status = transaction.get("status")
    if not isinstance(status, dict):
        raise ValueError("explorer transaction status is missing")
    confirmed = status.get("confirmed") is True
    confirmations = 0
    if confirmed:
        block_height = status.get("block_height")
        if isinstance(block_height, bool) or not isinstance(block_height, int) or block_height < 0:
            raise ValueError("confirmed transaction lacks a valid block height")
        tip_height = _get_json(f"{BASE_URL}/blocks/tip/height")
        if isinstance(tip_height, bool) or not isinstance(tip_height, int) or tip_height < block_height:
            raise ValueError("explorer tip height is invalid or behind transaction block")
        confirmations = tip_height - block_height + 1

    raw_outputs = transaction.get("vout")
    if not isinstance(raw_outputs, list) or not raw_outputs:
        raise ValueError("transaction outputs are missing")
    outputs = []
    for item in raw_outputs:
        if not isinstance(item, dict):
            raise ValueError("transaction output is malformed")
        script = item.get("scriptpubkey_address")
        value = item.get("value")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("transaction output value must be a non-negative integer in sats")
        outputs.append({"address": str(script or "").strip(), "value_sats": value})

    return {
        "network": "bitcoin",
        "txid": normalized_txid,
        "status": "CONFIRMED" if confirmed else "UNCONFIRMED",
        "confirmations": confirmations,
        "outputs": outputs,
        "source_url": f"https://mempool.space/tx/{normalized_txid}",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_origin": "LIVE_PUBLIC_EXPLORER_API",
        "pool_payout_verified": False,
        "revenue_realized": False,
        "external_actions_enabled": False,
    }

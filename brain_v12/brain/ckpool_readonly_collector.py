"""Read-only Solo CKPool public telemetry collector for Electronic Brain.

This module never starts a miner, submits shares, or treats pool statistics as
proof of local execution, a found block, payout, or realized revenue.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = "https://raw.stats.ckpool.org"
USER_AGENT = "ElectronicBrain-CKPool-ReadOnly/1.0"
_TIMEOUT_SECONDS = 8
_MAX_RESPONSE_BYTES = 64 * 1024
_BTC_ADDRESS_RE = re.compile(
    r"(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})\Z"
)


def validate_btc_address(address: str) -> str:
    """Validate an address-shaped identifier before using it in a URL path."""
    if not isinstance(address, str) or not _BTC_ADDRESS_RE.fullmatch(address):
        raise ValueError("invalid_or_missing_bitcoin_address")
    return address


def _fetch_text(url: str, *, timeout: int = _TIMEOUT_SECONDS) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"http_status_{response.status}")
        payload = response.read(_MAX_RESPONSE_BYTES + 1)
    if len(payload) > _MAX_RESPONSE_BYTES:
        raise RuntimeError("response_too_large")
    return payload.decode("utf-8", errors="replace")


def _parse_json_lines(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def collect_ckpool_readonly(
    address: str | None = None,
    *,
    fetcher=_fetch_text,
    observed_at: int | None = None,
) -> dict[str, Any]:
    """Fetch public pool telemetry and optionally address-level user telemetry."""
    observed = int(time.time()) if observed_at is None else int(observed_at)
    result: dict[str, Any] = {
        "schema": "electronic-brain.ckpool-readonly.v1",
        "observed_at_epoch": observed,
        "source": BASE_URL,
        "read_only": True,
        "pool_stats_available": False,
        "pool_stats": None,
        "user_stats_available": False,
        "user_stats": None,
        "local_miner_started": False,
        "local_hashrate_verified": False,
        "local_share_acceptance_verified": False,
        "block_found_verified": False,
        "payout_verified": False,
        "revenue_realized": False,
        "financial_execution_enabled": False,
    }
    try:
        pool_text = fetcher(f"{BASE_URL}/pool/pool.status")
        rows = _parse_json_lines(pool_text)
        if rows:
            result["pool_stats_available"] = True
            result["pool_stats"] = rows[:8]
    except (OSError, RuntimeError, urllib.error.URLError, TimeoutError) as exc:
        result["pool_error"] = type(exc).__name__

    if address is not None:
        valid_address = validate_btc_address(address)
        safe_path = urllib.parse.quote(valid_address, safe="")
        try:
            user_text = fetcher(f"{BASE_URL}/users/{safe_path}")
            user_rows = _parse_json_lines(user_text)
            if user_rows:
                result["user_stats_available"] = True
                # Do not echo the supplied address into an evidence artifact.
                result["user_stats"] = user_rows[:8]
            else:
                result["user_error"] = "no_parseable_user_statistics"
        except (OSError, RuntimeError, urllib.error.URLError, TimeoutError) as exc:
            result["user_error"] = type(exc).__name__
    result["evidence_limit"] = (
        "Pool-wide telemetry is aggregate. Address-level statistics, if returned, "
        "do not prove this device submitted shares. Solo mining has no guaranteed "
        "payout; only independently verified block and transaction evidence can "
        "establish a reward."
    )
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Read-only CKPool telemetry; never starts mining")
    parser.add_argument("--address", help="Optional public BTC payout address for user statistics")
    args = parser.parse_args()
    try:
        report = collect_ckpool_readonly(args.address)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))

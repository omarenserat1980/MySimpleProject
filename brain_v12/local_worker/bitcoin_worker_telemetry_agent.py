"""Forward real miner telemetry to Brain's authenticated worker API.

This agent never launches a miner and never controls wallets or pool accounts.
It reads telemetry from a separately configured local miner HTTP stats endpoint.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"REQUIRED_ENV_MISSING:{name}")
    return value


def validate_url(name: str, value: str, *, allow_local_http: bool = False) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "https" and not (
        allow_local_http and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise RuntimeError(f"HTTPS_REQUIRED:{name}")
    if not parsed.hostname:
        raise RuntimeError(f"INVALID_URL:{name}")
    return value.rstrip("/")


def get_json(url: str, *, token: str | None = None, timeout: float = 5.0) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP_STATUS:{response.status}")
        data = json.loads(response.read(1_000_000).decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED")
    return data


def post_json(url: str, payload: dict, token: str, timeout: float = 8.0) -> dict:
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status not in (200, 201, 202):
            raise RuntimeError(f"HTTP_STATUS:{response.status}")
        result = json.loads(response.read(1_000_000).decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED")
    return result


def build_report(stats: dict, worker_id: str) -> dict:
    # Deliberately require explicit fields; don't guess unit conversions or fabricate counters.
    hashrate = stats.get("hashrate_hs")
    accepted = stats.get("accepted_shares")
    rejected = stats.get("rejected_shares")
    stale = stats.get("stale_shares", 0)
    for name, value in (
        ("hashrate_hs", hashrate),
        ("accepted_shares", accepted),
        ("rejected_shares", rejected),
        ("stale_shares", stale),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(f"MINER_STATS_FIELD_INVALID:{name}")
        if value < 0 or value > 10**30:
            raise RuntimeError(f"MINER_STATS_FIELD_OUT_OF_RANGE:{name}")
    for name, value in (("accepted_shares", accepted), ("rejected_shares", rejected), ("stale_shares", stale)):
        if int(value) != value:
            raise RuntimeError(f"MINER_STATS_FIELD_NOT_INTEGER:{name}")
    return {
        "worker_id": worker_id,
        "algorithm": "sha256d",
        "hashrate_hs": float(hashrate),
        "accepted_shares": int(accepted),
        "rejected_shares": int(rejected),
        "stale_shares": int(stale),
        "observed_at": time.time(),
    }


def main() -> int:
    brain_base = validate_url("BRAIN_MINING_API_URL", required("BRAIN_MINING_API_URL"))
    stats_url = validate_url(
        "BRAIN_MINER_STATS_URL",
        required("BRAIN_MINER_STATS_URL"),
        allow_local_http=True,
    )
    token = required("BRAIN_MINING_WORKER_API_TOKEN")
    if len(token) < 32:
        raise RuntimeError("BRAIN_MINING_WORKER_API_TOKEN_TOO_SHORT")
    worker_id = required("BRAIN_MINING_WORKER_ID")
    interval = int(os.environ.get("BRAIN_MINING_HEARTBEAT_SECONDS", "30"))
    if not 10 <= interval <= 90:
        raise RuntimeError("BRAIN_MINING_HEARTBEAT_SECONDS_MUST_BE_10_TO_90")
    endpoint = brain_base + "/api/bitcoin-mining/worker/heartbeat"
    print("Brain physical-worker telemetry agent started; miner launch/control is disabled.", flush=True)
    while True:
        try:
            stats = get_json(stats_url)
            report = build_report(stats, worker_id)
            result = post_json(endpoint, report, token)
            if result.get("ok") is not True or result.get("worker_id") != worker_id:
                raise RuntimeError("BRAIN_HEARTBEAT_ACK_INVALID")
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            print(f"{stamp} heartbeat=accepted worker_id={worker_id} hashrate_hs={report['hashrate_hs']} accepted_shares_reported={report['accepted_shares']}", flush=True)
        except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError, OSError) as exc:
            # Avoid logging URLs, HTTP headers, tokens, or response bodies.
            print(f"heartbeat=failed error={type(exc).__name__}:{str(exc).splitlines()[0][:160]}", file=sys.stderr, flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Stopped by operator.", flush=True)
        raise SystemExit(130)
    except Exception as exc:
        print(f"startup=failed error={type(exc).__name__}:{str(exc)[:180]}", file=sys.stderr, flush=True)
        raise SystemExit(2)

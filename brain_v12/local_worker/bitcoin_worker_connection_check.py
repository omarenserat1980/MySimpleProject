"""Preflight the Brain worker connection without exposing credentials or starting a miner.

Required environment:
  BRAIN_MINING_API_URL=https://brain.example
  BRAIN_MINER_STATS_URL=http://127.0.0.1:PORT/stats
  BRAIN_MINING_WORKER_API_TOKEN=<secret of at least 32 characters>

This utility only performs GET requests. It never launches or controls mining.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"CONFIG_MISSING:{name}")
    return value


def validate_url(name: str, value: str, *, local_http: bool = False) -> str:
    parsed = urllib.parse.urlparse(value)
    local_host = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (
        local_http and parsed.scheme == "http" and local_host
    ):
        raise RuntimeError(f"URL_SCHEME_REJECTED:{name}")
    if not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError(f"URL_INVALID:{name}")
    return value.rstrip("/")


def get_json(url: str, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP_STATUS:{response.status}")
        value = json.loads(response.read(1_000_000).decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED")
    return value


def main() -> int:
    try:
        brain = validate_url(
            "BRAIN_MINING_API_URL", required("BRAIN_MINING_API_URL")
        )
        stats_url = validate_url(
            "BRAIN_MINER_STATS_URL",
            required("BRAIN_MINER_STATS_URL"),
            local_http=True,
        )
        token = required("BRAIN_MINING_WORKER_API_TOKEN")
        if len(token) < 32:
            raise RuntimeError("TOKEN_TOO_SHORT:minimum_32_characters")

        # Brain's authenticated status endpoint proves route reachability and token acceptance.
        status = get_json(brain + "/api/bitcoin-mining/worker/status", token)
        if status.get("ok") is not True:
            raise RuntimeError("BRAIN_STATUS_RESPONSE_INVALID")
        print("BRAIN_API=reachable AUTH=accepted")

        # Read-only check; do not infer physical mining from a successful HTTP response.
        stats = get_json(stats_url)
        required_fields = ("hashrate_hs", "accepted_shares", "rejected_shares")
        missing = [key for key in required_fields if key not in stats]
        if missing:
            raise RuntimeError("MINER_STATS_FIELDS_MISSING:" + ",".join(missing))
        print("MINER_STATS_ENDPOINT=reachable REQUIRED_FIELDS=present")
        print(f"BRAIN_REPORTED_WORKERS={status.get('worker_count', 'unknown')}")
        print("RESULT=preflight_passed; no heartbeat sent and mining not verified")
        return 0
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            print("PREFLIGHT_FAILED=authentication_rejected", file=sys.stderr)
        else:
            print(f"PREFLIGHT_FAILED=http_{exc.code}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError, OSError):
        print("PREFLIGHT_FAILED=connection_error", file=sys.stderr)
        return 2
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        # Error codes only; never print environment values, headers, or response bodies.
        print(f"PREFLIGHT_FAILED={str(exc)[:160]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

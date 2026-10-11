#!/usr/bin/env python3
"""Read-only check that Brain API health and cloud-worker health agree.

Examples:
  python tools/verify_cloud_worker_attestation_contract.py --api-url https://brain-control-plane-main.onrender.com
  python tools/verify_cloud_worker_attestation_contract.py --api-health api.json --worker-health worker.json

The live mode performs GET requests only. It never starts, queues, or mutates work.
A worker URL is optional because no production worker endpoint is currently proven.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def read_json_url(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status < 200 or response.status >= 300:
            raise ValueError(f"HTTP_STATUS_{response.status}:{url}")
        payload = json.loads(response.read(1_000_001).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{url}")
    return payload


def read_json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return payload


def assess(api_health: dict[str, Any], worker_health: dict[str, Any] | None = None) -> dict[str, Any]:
    api_worker = api_health.get("worker")
    api_worker = api_worker if isinstance(api_worker, dict) else {}
    api_verified = api_health.get("state") == "RUNNING" and api_worker.get("verified") is True
    result: dict[str, Any] = {
        "api_status": api_health.get("status"),
        "api_state": api_health.get("state"),
        "api_worker_state": api_worker.get("state"),
        "api_worker_verified": api_worker.get("verified") is True,
        "api_worker_reason": api_worker.get("reason"),
        "worker_endpoint_checked": worker_health is not None,
        "worker_endpoint_healthy": None,
        "status": "VERIFIED" if api_verified else "BLOCKED",
        "findings": [],
    }
    if not api_verified:
        result["findings"].append("API_DOES_NOT_ATTEST_A_VERIFIED_LIVE_WORKER")
    if worker_health is not None:
        is_worker = worker_health.get("service") == "brain-cloud-worker"
        workers = worker_health.get("workers")
        live_workers = isinstance(workers, list) and any(
            isinstance(item, dict) and item.get("status") in {"running", "success", "healthy"}
            for item in workers
        )
        endpoint_ok = worker_health.get("ok") is True and is_worker and live_workers
        result["worker_endpoint_healthy"] = endpoint_ok
        if not endpoint_ok:
            result["findings"].append("WORKER_ENDPOINT_DID_NOT_PROVE_HEALTHY_WORKERS")
        if api_verified and endpoint_ok:
            result["status"] = "VERIFIED"
        else:
            result["status"] = "BLOCKED"
        # The current Python API checks cloud-worker-heartbeat.json with a
        # preflight object; the .NET worker writes worker-heartbeat.json and
        # exposes its own registry. These are distinct attestations.
        if is_worker and not api_verified:
            result["findings"].append("WORKER_ENDPOINT_AND_API_ATTESTATION_NOT_YET_BRIDGED")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="https://brain-control-plane-main.onrender.com",
                        help="API base URL; only GET /health is called")
    parser.add_argument("--worker-url", help="Optional proven worker base URL; only GET /health is called")
    parser.add_argument("--api-health", type=Path, help="Read API health JSON from file instead of network")
    parser.add_argument("--worker-health", type=Path, help="Read worker health JSON from file instead of network")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    try:
        api = read_json_file(args.api_health) if args.api_health else read_json_url(args.api_url.rstrip("/") + "/health", args.timeout)
        worker = (read_json_file(args.worker_health) if args.worker_health else
                  read_json_url(args.worker_url.rstrip("/") + "/health", args.timeout) if args.worker_url else None)
        result = assess(api, worker)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)[:500]}, indent=2))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

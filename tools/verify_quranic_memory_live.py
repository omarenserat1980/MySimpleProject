#!/usr/bin/env python3
"""Read-only live probe for Quranic memory guidance endpoints.

Usage:
  BRAIN_BASE_URL=https://your-brain-service.onrender.com python tools/verify_quranic_memory_live.py

This script only issues GET requests. It does not send memory text, mutate data,
change settings, or trigger a deployment.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin

BASE_URL = os.environ.get("BRAIN_BASE_URL", "").strip().rstrip("/")
REQUIRED_PATHS = (
    "/api/quranic-core/memory-guidance",
    "/api/quranic-core/memory-guidance/review",
)


def get(url: str, timeout: float = 15.0) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "brain-readonly-live-probe/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(1_000_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read(2000).decode("utf-8", errors="replace")
        return exc.code, body
    except Exception as exc:
        print(f"FAIL: request error for {url}: {type(exc).__name__}: {exc}")
        return 0, ""


def main() -> int:
    if not BASE_URL:
        print("FAIL: set BRAIN_BASE_URL to the exact deployed Brain service URL.")
        return 2

    health_url = urljoin(BASE_URL + "/", "health")
    health_status, health_body = get(health_url)
    if health_status != 200:
        print(f"FAIL: GET /health returned HTTP {health_status}")
        return 1
    try:
        health = json.loads(health_body)
    except json.JSONDecodeError:
        print("FAIL: /health returned non-JSON content")
        return 1
    print(f"PASS: /health HTTP 200; version={health.get('version', 'unknown')}")

    openapi_url = urljoin(BASE_URL + "/", "openapi.json")
    schema_status, schema_body = get(openapi_url)
    if schema_status != 200:
        print(f"FAIL: GET /openapi.json returned HTTP {schema_status}")
        return 1
    try:
        schema = json.loads(schema_body)
    except json.JSONDecodeError:
        print("FAIL: /openapi.json returned invalid JSON")
        return 1

    paths = schema.get("paths", {})
    missing = [path for path in REQUIRED_PATHS if path not in paths]
    if missing:
        print("FAIL: expected memory-guidance routes are not registered:")
        for path in missing:
            print(f"  MISSING {path}")
        print("No writes were performed. Confirm the deployed commit includes the reviewed change.")
        return 1

    for path in REQUIRED_PATHS:
        methods = ", ".join(sorted(paths[path].keys())).upper()
        print(f"PASS: OpenAPI registers {path} [{methods}]")

    # GET only: confirm the read-only catalog endpoint responds.
    route_status, route_body = get(urljoin(BASE_URL + "/", REQUIRED_PATHS[0].lstrip("/")))
    if route_status != 200:
        print(f"FAIL: GET {REQUIRED_PATHS[0]} returned HTTP {route_status}")
        print(route_body[:500])
        return 1
    try:
        payload = json.loads(route_body)
    except json.JSONDecodeError:
        print("FAIL: memory-guidance catalog returned invalid JSON")
        return 1
    print(f"PASS: memory-guidance catalog responds with JSON; keys={sorted(payload.keys())}")
    print("PASS: read-only probe complete; no POST requests or mutations performed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

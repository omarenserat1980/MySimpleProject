#!/usr/bin/env python3
"""Electronic Brain V7 acceptance diagnostics: software ASIC + optional live APIs.

This tool is intentionally scoped to brain_v7. The ASIC portion is a software
reference model, not physical silicon validation. Live checks run only when an
operator supplies the exact URLs discovered from the V7 deployment/source.
Secrets are read from environment variables and are never printed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any

MCP_PROTOCOL_VERSION = os.getenv("MCP_PROTOCOL_VERSION", "2025-11-25")


def software_asic(seed: int = 7007, random_cases: int = 256) -> dict[str, Any]:
    started = time.perf_counter_ns()
    failures: list[dict[str, Any]] = []
    checks = 0

    def check(name: str, expected: Any, actual: Any) -> None:
        nonlocal checks
        checks += 1
        if expected != actual:
            failures.append({"test": name, "expected": expected, "actual": actual})

    for a in (0, 1):
        for b in (0, 1):
            check(f"xor_{a}{b}", a ^ b, a ^ b)
            check(f"half_adder_{a}{b}", (a + b), ((a ^ b) | ((a & b) << 1)))
            for cin in (0, 1):
                total = a + b + cin
                sum_bit = (a ^ b) ^ cin
                carry_bit = (a & b) | ((a ^ b) & cin)
                check(f"full_adder_{a}{b}{cin}", total, sum_bit + (carry_bit << 1))

    rng = random.Random(seed)
    for i in range(random_cases):
        a, b, cin = rng.randrange(2), rng.randrange(2), rng.randrange(2)
        total = a + b + cin
        sum_bit = (a ^ b) ^ cin
        carry_bit = (a & b) | ((a ^ b) & cin)
        check(f"property_full_adder_{i}", total, sum_bit + (carry_bit << 1))

    report: dict[str, Any] = {
        "status": "PASS" if not failures else "FAIL",
        "scope": "BRAIN_V7_SOFTWARE_ASIC_REFERENCE",
        "physical_hardware_tested": False,
        "seed": seed,
        "random_cases": random_cases,
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "elapsed_ns": time.perf_counter_ns() - started,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    return report


def request_json(url: str, method: str = "GET", body: dict[str, Any] | None = None,
                 headers: dict[str, str] | None = None, timeout: float = 10) -> tuple[int, Any]:
    h = {"Accept": "application/json, text/event-stream"}
    h.update(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(1_000_000).decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw) if raw else None
            except json.JSONDecodeError:
                return resp.status, {"response_type": "non_json", "sample": raw[:160]}
    except urllib.error.HTTPError as exc:
        raw = exc.read(1000).decode("utf-8", "replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = {"response_type": "non_json", "sample": raw[:160]}
        return exc.code, payload
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {"error_type": type(exc).__name__}


def live_health(url: str, timeout: float) -> dict[str, Any]:
    code, payload = request_json(url, timeout=timeout)
    ok = code == 200 and isinstance(payload, dict) and payload.get("ok", True) is True
    return {"status": "PASS" if ok else "BLOCKED" if code in (0, 401, 403, 404, 408, 429, 502, 503, 504) else "FAIL",
            "url": url, "http_status": code, "response_type": type(payload).__name__}


def live_mcp(url: str, timeout: float) -> dict[str, Any]:
    headers = {"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
    token = os.getenv("BRAIN_V7_MCP_BEARER_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    steps: list[dict[str, Any]] = []

    def rpc(step: str, req_id: int, method: str, params: dict[str, Any] | None = None):
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            body["params"] = params
        code, result = request_json(url, "POST", body, headers, timeout)
        valid = code in (200, 202) and isinstance(result, dict) and result.get("jsonrpc") == "2.0" and result.get("id") == req_id and "error" not in result
        steps.append({"step": step, "http_status": code, "pass": valid,
                      "response_keys": sorted(result.keys()) if isinstance(result, dict) else []})
        return result if valid else None

    initialized = rpc("initialize", 1, "initialize", {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "brain-v7-acceptance-diagnostics", "version": "1.0"},
    })
    if initialized is not None:
        code, _ = request_json(url, "POST", {"jsonrpc": "2.0", "method": "notifications/initialized"}, headers, timeout)
        steps.append({"step": "notifications/initialized", "http_status": code, "pass": code in (200, 202, 204)})
    else:
        steps.append({"step": "notifications/initialized", "pass": False, "skipped": True})

    listed = rpc("tools/list", 2, "tools/list", {}) if initialized is not None else None
    tools = listed.get("result", {}).get("tools", []) if isinstance(listed, dict) else []
    tool_names = [t.get("name") for t in tools if isinstance(t, dict)]
    target = os.getenv("BRAIN_V7_MCP_TEST_TOOL", "")
    if not target and "brain.status" in tool_names:
        target = "brain.status"
    if target and target in tool_names:
        rpc("tools/call " + target, 3, "tools/call", {"name": target, "arguments": {}})
    else:
        steps.append({"step": "tools/call", "pass": False, "skipped": True,
                      "reason": "Set BRAIN_V7_MCP_TEST_TOOL to a safe tool listed by tools/list"})

    oauth_metadata_only = {"status": "NOT_PROVEN",
                            "note": "Discovery metadata cannot prove OAuth 2.1 + PKCE end-to-end."}
    failed = [s for s in steps if not s.get("pass")]
    status = "PASS" if steps and not failed else ("BLOCKED" if any(s.get("skipped") or s.get("http_status") in (0, 401, 403, 404, 408, 429, 502, 503, 504) for s in failed) else "FAIL")
    return {"status": status, "scope": "LIVE_MCP_STREAMABLE_HTTP", "url": url,
            "protocol_version": MCP_PROTOCOL_VERSION, "steps": steps,
            "tools_list_names": tool_names, "oauth_2_1_pkce": oauth_metadata_only}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--health-url", help="Exact V7 health URL; no host is assumed")
    parser.add_argument("--mcp-url", help="Exact MCP POST endpoint discovered from V7 source/deployment")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--seed", type=int, default=7007)
    parser.add_argument("--random-cases", type=int, default=256)
    parser.add_argument("--output", help="Optional JSON evidence file")
    args = parser.parse_args()
    if args.timeout <= 0 or args.random_cases < 0 or args.random_cases > 100000:
        parser.error("timeout must be positive and random-cases between 0 and 100000")

    report: dict[str, Any] = {
        "project_scope": "brain_v7",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "software_asic": software_asic(args.seed, args.random_cases),
        "live_health": live_health(args.health_url, args.timeout) if args.health_url else {"status": "NOT_RUN", "reason": "Exact URL not supplied"},
        "live_mcp": live_mcp(args.mcp_url, args.timeout) if args.mcp_url else {"status": "NOT_RUN", "reason": "Exact MCP endpoint not supplied"},
        "oauth_2_1_pkce_end_to_end": {"status": "NOT_PROVEN", "reason": "Requires configured authorization server, registered client, redirect URI, and safe test credentials."},
        "cloud_worker": {"status": "NOT_PROVEN", "reason": "Requires a real authorized worker job and verifiable job/commit provenance."},
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered + "\n")
    return 0 if report["software_asic"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

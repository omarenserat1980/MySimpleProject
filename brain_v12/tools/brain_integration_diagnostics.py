#!/usr/bin/env python3
"""Read-only Electronic Brain integration diagnostics.

Separates deterministic local ASIC-logic checks from live MCP HTTP checks.
Never prints authorization tokens or response headers that may contain secrets.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

MCP_PROTOCOL_VERSION = "2025-11-25"


def local_asic_check() -> dict[str, Any]:
    """Deterministic XOR truth-table check; does not claim hardware execution."""
    cases = [
        (0, 0, 0),
        (0, 1, 1),
        (1, 0, 1),
        (1, 1, 0),
    ]
    failures = [
        {"a": a, "b": b, "expected": expected, "actual": a ^ b}
        for a, b, expected in cases
        if (a ^ b) != expected
    ]
    return {
        "status": "PASS" if not failures else "FAIL",
        "scope": "LOCAL_SOFTWARE_XOR_ONLY",
        "cases": len(cases),
        "failures": failures,
        "real_hardware_measurement": False,
    }


def http_json(url: str, method: str = "GET", body: dict[str, Any] | None = None,
              headers: dict[str, str] | None = None, timeout: float = 10.0
              ) -> tuple[int, Any]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(1_000_000).decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                payload = {"non_json_response": raw[:300]}
            return response.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read(1000).decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = {"non_json_response": raw[:300]}
        return exc.code, payload
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {"error_type": type(exc).__name__, "error": str(exc)[:200]}


def live_mcp_check(base_url: str, bearer_token: str | None = None, timeout: float = 10.0) -> dict[str, Any]:
    if timeout <= 0:
        raise ValueError('timeout must be greater than zero')
    base = base_url.rstrip("/")
    headers = {"MCP-Protocol-Version": MCP_PROTOCOL_VERSION}
    if bearer_token:
        headers["Authorization"] = "Bearer " + bearer_token

    checks: list[dict[str, Any]] = []

    # GET is informational: Streamable HTTP servers may legitimately return 405.
    status, payload = http_json(base + "/mcp", headers=headers, timeout=timeout)
    endpoint_probe = {
        "step": "GET /mcp (informational)",
        "http_status": status,
        "response_summary": summarize(payload),
    }

    def rpc(step: str, request_id: int, method: str,
            params: dict[str, Any] | None = None) -> tuple[int, Any]:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            body["params"] = params
        code, result = http_json(base + "/mcp", "POST", body, headers, timeout=timeout)
        valid = (
            code in (200, 202)
            and isinstance(result, dict)
            and result.get("jsonrpc") == "2.0"
            and result.get("id") == request_id
            and "error" not in result
        )
        checks.append({
            "step": step,
            "http_status": code,
            "pass": valid,
            "response_summary": summarize(result),
        })
        return code, result

    _, initialized = rpc("initialize", 1, "initialize", {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "brain-integration-diagnostics", "version": "1.0"},
    })

    # MCP requires the initialized notification before normal operations.
    if checks[-1]["pass"]:
        notify_code, notify_payload = http_json(
            base + "/mcp", "POST",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            headers, timeout=timeout,
        )
        notify_ok = notify_code in (200, 202, 204)
        checks.append({
            "step": "notifications/initialized",
            "http_status": notify_code,
            "pass": notify_ok,
            "response_summary": summarize(notify_payload),
        })
    else:
        notify_ok = False
        checks.append({
            "step": "notifications/initialized",
            "http_status": None,
            "pass": False,
            "skipped": True,
            "reason": "initialize did not succeed",
        })

    listed_tools = None
    if notify_ok:
        _, listed = rpc("tools/list", 2, "tools/list", {})
        if isinstance(listed, dict) and isinstance(listed.get("result"), dict):
            listed_tools = listed["result"].get("tools")
    else:
        checks.append({
            "step": "tools/list",
            "http_status": None,
            "pass": False,
            "skipped": True,
            "reason": "MCP initialize handshake did not succeed",
        })

    tool_available = isinstance(listed_tools, list) and any(
        isinstance(tool, dict) and tool.get("name") == "brain.status"
        for tool in listed_tools
    )
    if tool_available:
        _, called = rpc("tools/call brain.status", 3, "tools/call", {
            "name": "brain.status",
            "arguments": {},
        })
    else:
        called = None
        checks.append({
            "step": "tools/call brain.status",
            "http_status": None,
            "pass": False,
            "skipped": True,
            "reason": "brain.status was not confirmed in tools/list",
        })

    tool_result = called.get("result") if isinstance(called, dict) else None
    tool_call_ok = (
        isinstance(tool_result, dict)
        and isinstance(called, dict)
        and "error" not in called
        and tool_result.get("isError") is not True
        and isinstance(tool_result.get("content"), list)
    )
    for item in checks:
        if item["step"] == "tools/call brain.status":
            item["pass"] = bool(item["pass"] and tool_call_ok)

    # OAuth metadata discovery is reported independently; successful HTTP
    # discovery does not prove OAuth 2.1 + PKCE authorization flow compliance.
    oauth = []
    for path in (
        "/.well-known/oauth-protected-resource/mcp",
        "/.well-known/oauth-authorization-server",
    ):
        code, data = http_json(base + path, headers=headers, timeout=timeout)
        oauth.append({
            "path": path,
            "http_status": code,
            "metadata_discovered": code == 200 and isinstance(data, dict),
        })

    all_mcp = bool(checks) and all(item["pass"] for item in checks)
    blocked_codes = {0, 401, 403, 404, 408, 429, 500, 502, 503, 504}
    has_blocker = any(
        item.get("http_status") in blocked_codes or item.get("skipped")
        for item in checks
    )
    status_label = "PASS" if all_mcp and tool_call_ok else ("BLOCKED" if has_blocker else "FAIL")
    return {
        "status": status_label,
        "scope": "LIVE_HTTP_MCP",
        "base_url": base,
        "endpoint_probe": endpoint_probe,
        "checks": checks,
        "oauth_metadata_discovery": oauth,
        "oauth_2_1_pkce_flow_proven": False,
        "note": "Metadata discovery alone does not prove an OAuth 2.1 + PKCE flow.",
    }


def summarize(value: Any) -> Any:
    if not isinstance(value, dict):
        return value if value is None or isinstance(value, (str, int, float, bool)) else type(value).__name__
    # Do not echo arbitrary tool output, tokens, headers, or Brain memory.
    summary: dict[str, Any] = {}
    for key in ("name", "protocolVersion", "transport", "jsonrpc", "id", "error"):
        if key in value:
            summary[key] = value[key]
    if isinstance(value.get("result"), dict):
        result = value["result"]
        summary["result_keys"] = sorted(result.keys())
        if isinstance(result.get("tools"), list):
            summary["tool_names"] = [
                str(item.get("name", "")) for item in result["tools"] if isinstance(item, dict)
            ]
        if isinstance(result.get("content"), list):
            summary["content_items"] = len(result["content"])
    if "error_type" in value:
        summary["error_type"] = value["error_type"]
        summary["error"] = value.get("error")
    if "non_json_response" in value:
        summary["non_json_response"] = value["non_json_response"]
    return summary or {"response_type": type(value).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Live Brain base URL; omit to run local checks only")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout in seconds")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")

    report: dict[str, Any] = {"local_asic": local_asic_check()}
    if args.base_url:
        import os
        report["live_mcp"] = live_mcp_check(
            args.base_url,
            bearer_token=os.environ.get("BRAIN_DIAGNOSTICS_BEARER_TOKEN"),
            timeout=args.timeout,
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["local_asic"]["status"] != "PASS" else (
        1 if "live_mcp" in report and report["live_mcp"]["status"] != "PASS" else 0
    )


if __name__ == "__main__":
    sys.exit(main())

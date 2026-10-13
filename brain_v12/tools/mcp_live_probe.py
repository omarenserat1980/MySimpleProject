#!/usr/bin/env python3
"""Read-only MCP Streamable HTTP probe for Electronic Brain.

Checks GET /mcp, initialize, tools/list, and an explicitly selected tools/call.
It never prints request headers, bearer tokens, or raw response bodies.
Live results are observations, not deployment or security certification.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_PROTOCOL = "2026-07-28"


def request_json(url: str, payload: dict[str, Any] | None, protocol: str,
                 timeout: float, bearer: str | None) -> tuple[int, Any]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": protocol,
        "User-Agent": "ElectronicBrain-MCP-Diagnostic/1.0",
    }
    data = None
    method = "GET"
    if payload is not None:
        method = "POST"
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = response.status
            raw = response.read(1_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read(1_000_000).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, {"transport_error": type(exc).__name__}
    try:
        parsed = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        parsed = {"non_json_response": True, "bytes": len(raw)}
    return status, parsed


def rpc_ok(status: int, body: Any, expected_id: int) -> bool:
    return (
        200 <= status < 300 and isinstance(body, dict)
        and body.get("jsonrpc") == "2.0"
        and body.get("id") == expected_id
        and "result" in body and "error" not in body
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True,
                        help="MCP endpoint URL, e.g. https://host.example/mcp")
    parser.add_argument("--protocol", default=DEFAULT_PROTOCOL)
    parser.add_argument("--tool", default="brain.status",
                        help="Tool to call after discovery (default: read-only brain.status)")
    parser.add_argument("--arguments", default="{}",
                        help="JSON object for the selected tool; default is empty")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--bearer-env", default="BRAIN_MCP_BEARER_TOKEN",
                        help="Environment variable containing optional bearer token")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    if not base.startswith(("https://", "http://")):
        parser.error("--url must use http:// or https://")
    try:
        call_args = json.loads(args.arguments)
        if not isinstance(call_args, dict):
            raise ValueError("arguments must be a JSON object")
    except ValueError as exc:
        parser.error(f"invalid --arguments: {exc}")

    token = os.environ.get(args.bearer_env) or None
    results: list[dict[str, Any]] = []
    get_status, get_body = request_json(base, None, args.protocol, args.timeout, token)
    results.append({
        "step": "GET endpoint", "http_status": get_status,
        "pass": 200 <= get_status < 300 and isinstance(get_body, dict),
        "summary": get_body if isinstance(get_body, dict) and
                   set(get_body).issubset({"name", "protocolVersion", "transport", "error"})
                   else {"response_type": type(get_body).__name__},
    })

    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": args.protocol,
                       "capabilities": {}, "clientInfo": {
                           "name": "brain-live-diagnostic", "version": "1.0"}}}
    status, body = request_json(base, init, args.protocol, args.timeout, token)
    init_ok = rpc_ok(status, body, 1)
    results.append({"step": "initialize", "http_status": status, "pass": init_ok,
                    "summary": body.get("result", {}).get("serverInfo", {})
                    if isinstance(body, dict) else {}})
    if not init_ok:
        return report(results, False)

    status, body = request_json(base, {"jsonrpc": "2.0", "id": 2,
                                       "method": "tools/list", "params": {}},
                                args.protocol, args.timeout, token)
    listing_ok = rpc_ok(status, body, 2)
    tool_names = []
    if listing_ok:
        tools = body["result"].get("tools", [])
        tool_names = [x.get("name") for x in tools if isinstance(x, dict)]
    results.append({"step": "tools/list", "http_status": status,
                    "pass": listing_ok, "tool_count": len(tool_names),
                    "tools": tool_names[:100]})
    if not listing_ok or args.tool not in tool_names:
        if listing_ok:
            results.append({"step": "tools/call", "http_status": None, "pass": False,
                            "summary": "selected tool is not advertised; call skipped"})
        return report(results, False)

    status, body = request_json(
        base, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
               "params": {"name": args.tool, "arguments": call_args}},
        args.protocol, args.timeout, token)
    call_ok = rpc_ok(status, body, 3)
    result = body.get("result", {}) if isinstance(body, dict) else {}
    structured = result.get("structuredContent", {}) if isinstance(result, dict) else {}
    # Do not print tool result payloads; it may contain private operational data.
    results.append({"step": "tools/call", "http_status": status, "pass": call_ok,
                    "tool": args.tool,
                    "tool_is_error": result.get("isError") if isinstance(result, dict) else None,
                    "structured_status": structured.get("status")
                    if isinstance(structured, dict) else None})
    return report(results, call_ok and not bool(results[-1].get("tool_is_error")))


def report(results: list[dict[str, Any]], success: bool) -> int:
    print(json.dumps({"diagnostic": "brain-mcp-live-probe",
                      "overall_pass": success,
                      "evidence_scope": "live HTTP observations only; not OAuth/PKCE certification",
                      "steps": results}, ensure_ascii=False, indent=2))
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

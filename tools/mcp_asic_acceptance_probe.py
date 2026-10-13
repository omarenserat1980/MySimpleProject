#!/usr/bin/env python3
"""Read-only MCP/ASIC acceptance probe for Electronic Brain.

Usage:
  BRAIN_MCP_URL=https://host.example/mcp python tools/mcp_asic_acceptance_probe.py
  BRAIN_MCP_TOKEN=... BRAIN_MCP_URL=... python tools/mcp_asic_acceptance_probe.py

The token is read from the environment and is never printed. This script does
not change Render, secrets, repository state, or simulator state. It calls only
brain.status; it never executes an ASIC operation automatically.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = "https://electronic-brain-v12-gwwg.onrender.com/mcp"
PROTOCOL_VERSION = "2026-07-28"


def request(url: str, method: str, payload: dict[str, Any] | None = None,
            token: str = "") -> tuple[int, dict[str, Any] | None, str]:
    headers = {"Accept": "application/json", "MCP-Protocol-Version": PROTOCOL_VERSION}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read(1_000_000).decode("utf-8", errors="replace")
            try:
                body = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                body = None
            return response.status, body, ""
    except urllib.error.HTTPError as exc:
        raw = exc.read(1_000_000).decode("utf-8", errors="replace")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = None
        return exc.code, body, ""
    except Exception as exc:
        # Error text is restricted to the exception class to avoid leaking URLs
        # or request details that may contain sensitive material.
        return 0, None, type(exc).__name__


def rpc(url: str, method: str, request_id: int, token: str) -> tuple[int, dict[str, Any] | None, str]:
    return request(url, "POST", {
        "jsonrpc": "2.0", "id": request_id, "method": method,
        "params": {"protocolVersion": PROTOCOL_VERSION} if method == "initialize" else {},
    }, token)


def main() -> int:
    url = os.getenv("BRAIN_MCP_URL", DEFAULT_URL).strip()
    token = os.getenv("BRAIN_MCP_TOKEN", "").strip()
    if not url.startswith("https://") or not url.endswith("/mcp"):
        print("CONFIG_ERROR: BRAIN_MCP_URL must be an HTTPS URL ending in /mcp")
        return 2

    print("Target:", url)
    print("Credential supplied:", "yes (value hidden)" if token else "no")
    # Unauthenticated check is deliberately first and never includes a token.
    status, body, error = request(url, "GET")
    print("GET /mcp:", status or "NETWORK_ERROR",
          ("error=" + error) if error else "",
          ("body=" + json.dumps(body, ensure_ascii=False)) if body is not None else "")
    unauth_status, unauth_body, unauth_error = rpc(url, "initialize", 1, "")
    print("Unauthenticated initialize:", unauth_status or "NETWORK_ERROR",
          ("error=" + unauth_error) if unauth_error else "",
          ("body=" + json.dumps(unauth_body, ensure_ascii=False)) if unauth_body is not None else "")
    if not token:
        print("STOP: no BRAIN_MCP_TOKEN supplied; authenticated MCP sequence not attempted.")
        print("Acceptance: NOT PROVEN")
        return 1

    status, body, error = rpc(url, "initialize", 2, token)
    print("initialize:", status or "NETWORK_ERROR",
          ("error=" + error) if error else "",
          ("body=" + json.dumps(body, ensure_ascii=False)) if body is not None else "")
    if status != 200 or not isinstance(body, dict) or "result" not in body:
        print("STOP: initialize did not return a JSON-RPC result.")
        print("Acceptance: NOT PROVEN")
        return 1

    status, body, error = rpc(url, "tools/list", 3, token)
    print("tools/list:", status or "NETWORK_ERROR",
          ("error=" + error) if error else "")
    if status != 200 or not isinstance(body, dict) or "result" not in body:
        print("STOP: tools/list did not return a JSON-RPC result.")
        print("Acceptance: NOT PROVEN")
        return 1

    tools = body.get("result", {}).get("tools", [])
    names = [item.get("name", "") for item in tools if isinstance(item, dict)]
    print("Tool names:", json.dumps(names, ensure_ascii=False))
    # Only call the known read-only status tool; never guess ASIC arguments.
    if "brain.status" not in names:
        print("STOP: brain.status is not advertised; tools/call not attempted.")
        print("Acceptance: NOT PROVEN")
        return 1
    status, body, error = request(url, "POST", {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "brain.status", "arguments": {}},
    }, token)
    print("tools/call brain.status:", status or "NETWORK_ERROR",
          ("error=" + error) if error else "",
          ("body=" + json.dumps(body, ensure_ascii=False)) if body is not None else "")
    asic_tools = [name for name in names if "asic" in name.lower()]
    print("ASIC tools discovered:", json.dumps(asic_tools, ensure_ascii=False))
    print("ASIC live execution: NOT ATTEMPTED (tool contract and explicit test vector required)")
    ok = status == 200 and isinstance(body, dict) and "result" in body
    print("MCP read-only sequence:", "PASS" if ok else "FAIL")
    print("Full MCP + ASIC acceptance:", "NOT PROVEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

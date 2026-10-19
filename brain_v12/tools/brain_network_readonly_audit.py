#!/usr/bin/env python3
"""Collect a read-only audit of Brain's local network/ASIC/mining APIs.

The default mode calls only local status endpoints over loopback. The optional
--include-network-diagnostics flag calls an aggregate diagnostic endpoint that
may probe a configured gateway's TCP ports. No mode scans a LAN, contacts an
ASIC, changes configuration, or starts mining.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# These endpoints are intended to be local read-only status surfaces. The
# aggregated network-diagnostics endpoint is deliberately opt-in because its
# current report may perform TCP reachability probes against a configured
# gateway, which exceeds a strictly loopback-only audit.
ENDPOINTS = {
    "directory_status": "/api/network-directory/status",
    "directory_devices": "/api/network-directory/devices",
    "directory_overview": "/api/network-directory/overview",
    "asic_bridge": "/api/asic-bridge/status",
    "mining_readiness": "/api/mining-node/readiness",
    "follow_up": "/api/follow-up/status",
}
OPTIONAL_NETWORK_DIAGNOSTICS_ENDPOINT = "/api/network-diagnostics/report"


def fetch_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(base_url + path, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("API response must be a JSON object")
            return {"http_status": response.status, "data": payload}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return {"http_status": None, "error": type(exc).__name__, "detail": str(exc)[:300]}


def build_report(
    base_url: str,
    timeout: float = 3.0,
    include_network_diagnostics: bool = False,
) -> dict[str, Any]:
    results = {name: fetch_json(base_url, path, timeout) for name, path in ENDPOINTS.items()}
    if include_network_diagnostics:
        results["network_diagnostics"] = fetch_json(
            base_url, OPTIONAL_NETWORK_DIAGNOSTICS_ENDPOINT, timeout
        )
    else:
        results["network_diagnostics"] = {
            "skipped": True,
            "reason": "OPT_IN_REQUIRED_ENDPOINT_MAY_PROBE_CONFIGURED_GATEWAY",
        }

    def data(name: str) -> dict[str, Any]:
        result = results[name]
        value = result.get("data", {})
        return value if isinstance(value, dict) else {}

    devices = data("directory_devices").get("items", [])
    asic = data("asic_bridge")
    mining = data("mining_readiness")
    directory = data("directory_status")
    required_results = [results[name] for name in ENDPOINTS]
    if include_network_diagnostics:
        required_results.append(results["network_diagnostics"])
    all_reachable = all(item.get("http_status") == 200 for item in required_results)
    return {
        "schema": "brain-network-readonly-audit/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "network_diagnostics_included": include_network_diagnostics,
        "mode": (
            "READ_ONLY_WITH_OPTIONAL_GATEWAY_DIAGNOSTICS"
            if include_network_diagnostics
            else "READ_ONLY_NO_SCAN_NO_CONFIGURATION_CHANGES"
        ),
        "results": results,
        "conclusion": {
            "brain_local_api_reachable": all_reachable,
            "known_device_count": len(devices) if isinstance(devices, list) else None,
            "known_asic_count": sum(1 for d in devices if isinstance(d, dict) and str(d.get("role", "")).lower() == "asic") if isinstance(devices, list) else None,
            "asic_contacted": asic.get("device_contacted", False),
            "network_scan_performed": directory.get("network_scan_performed", False),
            "settings_changed": False,
            "mining_started": asic.get("mining_started", False),
            "real_mining_verified": mining.get("real_mining_ready", False),
            "limitations": [
                "Gateway reachability does not identify an ASIC.",
                "Only devices already present in Brain's local inventory are counted.",
                "This audit does not scan the LAN, contact an ASIC, change settings, or start mining.",
                *(
                    ["Optional network diagnostics may perform TCP reachability probes against the configured gateway."]
                    if include_network_diagnostics else []
                ),
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8012")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--output", default="", help="Output JSON path; default creates a timestamped evidence file")
    parser.add_argument(
        "--include-network-diagnostics",
        action="store_true",
        help="Explicitly call /api/network-diagnostics/report; this endpoint may probe a configured gateway",
    )
    args = parser.parse_args()
    if args.timeout <= 0 or args.timeout > 15:
        parser.error("--timeout must be between 0 and 15 seconds")
    from urllib.parse import urlparse
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.port not in {None, 8012}:
        parser.error("Only local loopback HTTP on port 8012 is permitted")
    base_url = args.base_url.rstrip("/")
    report = build_report(base_url, args.timeout, args.include_network_diagnostics)
    output = Path(args.output) if args.output else Path("evidence") / ("brain_network_readonly_audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents accidental replacement of previous evidence.
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"evidence_path": str(output), **report["conclusion"]}, ensure_ascii=False, indent=2))
    return 0 if report["conclusion"]["brain_local_api_reachable"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

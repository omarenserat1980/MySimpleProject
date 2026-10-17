"""Read-only preflight for a Brain connectivity gateway, never a mining worker.

This module checks only whether a physical device can connect to Brain. It does
not require a local miner, local pool configuration, Termux, thermal sensors, or
local compute resources because mining computation must not run on the gateway.
"""
from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Mapping, Any


def _termux_detected(env: Mapping[str, str]) -> bool:
    try:
        return bool(env.get("TERMUX_VERSION")) or Path(
            "/data/data/com.termux/files/usr"
        ).is_dir()
    except OSError:
        return bool(env.get("TERMUX_VERSION"))


def inspect_node(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Return safe gateway readiness metadata without exposing environment values."""
    env = os.environ if env is None else env
    brain_url_configured = bool(env.get("V12_BRAIN_URL") or env.get("BRAIN_URL"))
    gateway_auth_configured = bool(
        env.get("BRAIN_AGENT_KEY")
        or env.get("BRAIN_WORKER_TOKEN")
        or env.get("V12_AGENT_KEY")
    )
    blockers: list[str] = []
    if not brain_url_configured:
        blockers.append("BRAIN_CONTROL_PLANE_URL_NOT_CONFIGURED")
    if not gateway_auth_configured:
        blockers.append("GATEWAY_AUTH_TOKEN_NOT_CONFIGURED")

    return {
        "schema_version": "2.0",
        "component": "brain-connectivity-gateway-preflight",
        "status": "BLOCKED" if blockers else "GATEWAY_CONFIGURED_NOT_VERIFIED",
        "execution_mode": "GATEWAY_CONNECTIVITY_PREFLIGHT_ONLY",
        "gateway_configured": not blockers,
        "gateway_identity_verified": False,
        "node_verified": False,
        "real_mining_started": False,
        "local_mining_allowed": False,
        "physical_device_computation_allowed": False,
        "pool_contacted": False,
        "accepted_shares_verified": False,
        "revenue_verified": False,
        "environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "termux_detected": _termux_detected(env),
            "brain_url_configured": brain_url_configured,
            "gateway_auth_configured": gateway_auth_configured,
        },
        "blockers": blockers,
        "verification_required": [
            "trusted gateway identity and authenticated connection to Brain",
            "fresh Brain-side gateway heartbeat",
            "implemented and reviewed Brain-owned software mining backend",
            "independently verified pool accepted-share evidence bound to the Brain runtime",
            "independent payout and cost evidence before revenue or profit claims",
        ],
        "security_note": (
            "Secret values, pool URLs, worker names, hostnames, and device identifiers "
            "are not emitted. This gateway does not host or launch mining computation."
        ),
    }


def main() -> int:
    import json
    result = inspect_node()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "GATEWAY_CONFIGURED_NOT_VERIFIED" else 2


if __name__ == "__main__":
    import sys
    sys.exit(main())

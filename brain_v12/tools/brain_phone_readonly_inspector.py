"""Read-only local resource inspection; no network, mining, or activation."""
from __future__ import annotations
import argparse
import json
from typing import Any
from brain_v12.tools.brain_live_resource_agent import collect_resource_snapshot


def inspect_local_resources(node_id: str = "local-device-unverified") -> dict[str, Any]:
    """Read only OS-reported facts; never enroll or contact a device."""
    if not isinstance(node_id, str) or not node_id.strip() or len(node_id) > 128:
        raise ValueError("INVALID_NODE_ID")
    s = collect_resource_snapshot()
    return {
        "schema_version": "1.0",
        "component": "brain-phone-readonly-inspector",
        "node_id": node_id,
        "mode": "READ_ONLY_LOCAL_MEASUREMENT",
        "state": "MEASURED_LOCAL_UNVERIFIED",
        "synthetic": False,
        "measurement_source": "LOCAL_OS_SELF_REPORTED",
        "observed_at_utc": s.get("observed_at_utc"),
        "resources": {
            "os": s.get("os"),
            "os_release": s.get("os_release"),
            "architecture": s.get("architecture"),
            "python_version": s.get("python_version"),
            "cpu_logical_count": s.get("cpu_logical_count"),
            "available_memory_bytes": s.get("available_memory_bytes"),
            "disk": s.get("disk"),
            "load_average_1_5_15": s.get("load_average_1_5_15"),
        },
        "resource_metrics_are_self_reported": True,
        "device_identity_verified": False,
        "independent_hardware_attestation": False,
        "network_calls_performed": False,
        "heartbeat_sent": False,
        "device_registered": False,
        "activation_performed": False,
        "tasks_dispatched": False,
        "mining_started": False,
        "pool_connection_attempted": False,
        "mining_verified": False,
        "revenue_verified": False,
        "note": "Local OS measurements only; not independent hardware attestation or proof of a remote phone.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--node-id", default="local-device-unverified")
    args = p.parse_args(argv)
    print(json.dumps(inspect_local_resources(args.node_id), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

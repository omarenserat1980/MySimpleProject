"""Fail-closed validation for locally collected Brain Phone evidence.

This validates structure and safety claims only. It cannot authenticate a device,
prove physical hardware, or independently attest measurements.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

REQUIRED_FALSE_FLAGS = (
    "device_identity_verified",
    "independent_hardware_attestation",
    "network_calls_performed",
    "heartbeat_sent",
    "device_registered",
    "activation_performed",
    "tasks_dispatched",
    "mining_started",
    "pool_connection_attempted",
    "mining_verified",
    "revenue_verified",
)


def validate_phone_evidence(payload: Any) -> dict[str, Any]:
    """Return a conservative validation result; never upgrades trust status."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return {
            "valid": False,
            "trust_state": "UNTRUSTED",
            "independent_verification": False,
            "errors": ["PAYLOAD_MUST_BE_OBJECT"],
        }

    required = {
        "schema_version", "component", "node_id", "mode", "state", "synthetic",
        "measurement_source", "observed_at_utc", "resources",
        "resource_metrics_are_self_reported",
    }
    missing = sorted(required - payload.keys())
    if missing:
        errors.append("MISSING_FIELDS:" + ",".join(missing))

    expected = {
        "component": "brain-phone-readonly-inspector",
        "mode": "READ_ONLY_LOCAL_MEASUREMENT",
        "state": "MEASURED_LOCAL_UNVERIFIED",
        "synthetic": False,
        "measurement_source": "LOCAL_OS_SELF_REPORTED",
        "resource_metrics_are_self_reported": True,
    }
    for key, value in expected.items():
        if key in payload and payload[key] != value:
            errors.append("UNEXPECTED_VALUE:" + key)

    node_id = payload.get("node_id")
    if not isinstance(node_id, str) or not node_id.strip() or len(node_id) > 128:
        errors.append("INVALID_NODE_ID")

    timestamp = payload.get("observed_at_utc")
    if not isinstance(timestamp, str) or not timestamp:
        errors.append("INVALID_OBSERVED_AT_UTC")
    else:
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            errors.append("INVALID_OBSERVED_AT_UTC")

    resources = payload.get("resources")
    if not isinstance(resources, dict):
        errors.append("RESOURCES_MUST_BE_OBJECT")
    else:
        for key in ("cpu_logical_count", "available_memory_bytes"):
            value = resources.get(key)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                errors.append("INVALID_RESOURCE:" + key)
        disk = resources.get("disk")
        if disk is not None:
            if not isinstance(disk, dict):
                errors.append("INVALID_RESOURCE:disk")
            else:
                for key in ("total_bytes", "free_bytes"):
                    value = disk.get(key)
                    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                        errors.append("INVALID_RESOURCE:disk." + key)
                total, free = disk.get("total_bytes"), disk.get("free_bytes")
                if isinstance(total, int) and isinstance(free, int) and free > total:
                    errors.append("INVALID_RESOURCE:disk.free_bytes_exceeds_total")

    for key in REQUIRED_FALSE_FLAGS:
        if payload.get(key) is not False:
            errors.append("SAFETY_FLAG_NOT_FALSE:" + key)

    return {
        "valid": not errors,
        "trust_state": "UNTRUSTED",
        "independent_verification": False,
        "eligible_for_activation": False,
        "eligible_for_mining": False,
        "errors": errors,
        "note": "Structural validation only; does not authenticate device identity or attest physical hardware.",
    }

"""Execution-mode thermal sensor policy for Brain.

Estimated temperatures support simulation but never satisfy a physical
hardware sensor requirement.
"""
from __future__ import annotations

CLOUD_SIMULATION = "CLOUD_SIMULATION"
REAL_HARDWARE = "REAL_HARDWARE"


def thermal_sensor_policy_gate(
    execution_mode: str,
    *,
    sensor_required: bool,
    sensor_available: bool,
    sensor_reading_valid: bool,
    approved_alternative: bool = False,
) -> dict:
    """Return an auditable allow/block decision without probing hardware.

    approved_alternative must only be set after an applicable safety policy
    explicitly authorizes and verifies that alternative. It is not inferred
    from a software estimate.
    """
    mode = execution_mode.strip().upper() if isinstance(execution_mode, str) else ""

    if mode == CLOUD_SIMULATION:
        return {
            "allowed": True,
            "status": "SIMULATION_ALLOWED",
            "execution_mode": CLOUD_SIMULATION,
            "thermal_source": "REAL_SENSOR" if sensor_available and sensor_reading_valid else "ESTIMATED",
            "evidence_class": "SIMULATION",
            "physical_safety_claim": False,
        }

    if mode != REAL_HARDWARE:
        return {
            "allowed": False,
            "status": "BLOCKED_UNKNOWN_EXECUTION_MODE",
            "execution_mode": mode or "UNKNOWN",
            "reason": "EXECUTION_MODE_MUST_BE_EXPLICIT",
            "evidence_class": "UNVERIFIED",
        }

    valid_sensor = sensor_available and sensor_reading_valid
    if sensor_required and not valid_sensor and not approved_alternative:
        return {
            "allowed": False,
            "status": "BLOCKED_REQUIRED_THERMAL_SENSOR",
            "execution_mode": REAL_HARDWARE,
            "reason": "REQUIRED_THERMAL_SENSOR_UNAVAILABLE_OR_INVALID",
            "evidence_class": "REAL_HARDWARE",
        }

    if not valid_sensor and approved_alternative:
        thermal_source = "APPROVED_ALTERNATIVE"
    elif valid_sensor:
        thermal_source = "REAL_SENSOR"
    else:
        thermal_source = "NOT_REQUIRED_BY_POLICY"

    return {
        "allowed": True,
        "status": "REAL_HARDWARE_POLICY_SATISFIED",
        "execution_mode": REAL_HARDWARE,
        "thermal_source": thermal_source,
        "evidence_class": "REAL_HARDWARE",
        "physical_safety_claim": False,
    }

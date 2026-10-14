"""Deterministic local simulator for design-factory steps.

This module performs no network, filesystem, subprocess, hardware, mining, or
manufacturing actions. Its outputs are explicitly SIMULATED and must never be
interpreted as physical-world evidence.
"""
from __future__ import annotations

import hashlib
import json

SIMULATOR_ID = "brain.design_factory.local_simulator.v1"
ALLOWED_DOMAINS = {
    "requirements",
    "research",
    "architecture",
    "software",
    "rtl",
    "verification",
    "physical_design",
    "security",
    "testing",
    "documentation",
    "unknown",
}


def simulate_step(step: dict) -> dict:
    """Return deterministic synthetic evidence for one allowlisted domain."""
    if not isinstance(step, dict):
        raise ValueError("step must be a dictionary")
    step_id = step.get("step_id")
    domain = step.get("domain")
    if not isinstance(step_id, str) or not step_id.strip():
        raise ValueError("step_id is required")
    if domain not in ALLOWED_DOMAINS:
        raise ValueError("domain is not allowlisted for simulation")

    payload = {
        "simulator": SIMULATOR_ID,
        "step_id": step_id,
        "domain": domain,
        "outcome": "synthetic_step_completed",
        "physical_execution": False,
        "external_side_effects": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return {
        "status": "SIMULATED",
        "evidence": {
            "kind": "SIMULATION",
            **payload,
            "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "limitations": [
                "not_hardware_evidence",
                "not_manufacturing_evidence",
                "not_mining_evidence",
                "not_revenue_evidence",
            ],
        },
    }

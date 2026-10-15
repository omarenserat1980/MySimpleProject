"""Simulation-first registry and activation gate for Brain phone resource nodes.

This module never discovers phones, sends network requests, runs jobs, mines, or
activates real devices. Simulation output is explicitly labelled as synthetic.
Real activation is deliberately not implemented here; this module only evaluates
whether required independent evidence is present and fails closed otherwise.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"
REQUIRED_EVIDENCE = (
    "device_registration",
    "authenticated_heartbeat",
    "independent_resource_attestation",
    "user_consent",
    "secure_transport",
)


def simulate_phone_node(node_id: str = "phone-sim-001") -> dict[str, Any]:
    """Return deterministic synthetic data, never host or device measurements."""
    if not isinstance(node_id, str) or not node_id.strip() or len(node_id) > 128:
        raise ValueError("INVALID_NODE_ID")
    return {
        "schema_version": SCHEMA_VERSION,
        "component": "brain-phone-base",
        "node_id": node_id,
        "mode": "SIMULATOR",
        "state": "SIMULATED",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "synthetic": True,
        "resource_metrics_are_self_reported": False,
        "resources": {
            "cpu_logical_count": 8,
            "available_memory_bytes": 2 * 1024**3,
            "storage_free_bytes": 16 * 1024**3,
            "network": "SIMULATED",
            "battery_percent": 75,
        },
        "real_device_connected": False,
        "real_activation_performed": False,
        "tasks_dispatched": False,
        "mining_started": False,
        "mining_verified": False,
        "revenue_verified": False,
    }


def evaluate_activation_gate(evidence: Any) -> dict[str, Any]:
    """Assess evidence presence only; never activate a real node."""
    if not isinstance(evidence, dict):
        evidence = {}
    missing: list[str] = []
    for name in REQUIRED_EVIDENCE:
        item = evidence.get(name)
        if (
            not isinstance(item, dict)
            or item.get("verified") is not True
            or not isinstance(item.get("source"), str)
            or not item["source"].strip()
            or item["source"].strip().lower() in {"self_reported", "user_claim", "simulator"}
            or not isinstance(item.get("digest"), str)
            or len(item["digest"].strip()) < 16
        ):
            missing.append(name)
    return {
        "schema_version": SCHEMA_VERSION,
        "component": "brain-phone-base",
        "state": "BLOCKED" if missing else "ELIGIBLE_FOR_MANUAL_REVIEW",
        "missing_evidence": missing,
        "real_activation_performed": False,
        "automatic_activation_allowed": False,
        "tasks_dispatched": False,
        "mining_started": False,
        "revenue_verified": False,
        "note": (
            "Evidence fields are not independently validated by this module. "
            "A trusted server-side verifier and explicit operator approval are "
            "required; this result never activates a device."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-id", default="phone-sim-001")
    parser.add_argument("--evidence-json", help="Optional evidence JSON file for gate evaluation")
    args = parser.parse_args()
    if args.evidence_json:
        with open(args.evidence_json, encoding="utf-8") as handle:
            result = evaluate_activation_gate(json.load(handle))
    else:
        result = simulate_phone_node(args.node_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

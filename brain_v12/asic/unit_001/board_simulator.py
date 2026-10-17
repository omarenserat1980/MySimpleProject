#!/usr/bin/env python3
"""Simulation-only BRAIN-ASIC-001 board/chip bench.

This models a hypothetical controller/ASIC interface and validates software
plumbing. It DOES NOT emulate transistor-level ASIC timing, fabricate hardware,
measure power/temperature/hashrate, connect to a pool, or submit shares.
Every synthetic telemetry field is explicitly marked simulated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from typing import Any


SIMULATION_ONLY = True
MODEL_ID = "BRAIN-ASIC-001-SOFTWARE-BOARD-MODEL-v1"


def sha256d(data: bytes) -> bytes:
    """Return Bitcoin-style double SHA-256 of arbitrary bytes."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def known_answer_test() -> dict[str, Any]:
    # Standard known-answer vector: SHA256d of the empty byte string.
    expected = "5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9456"
    actual = sha256d(b"").hex()
    return {
        "test_id": "sha256d-empty-message-known-answer",
        "expected_digest_hex": expected,
        "actual_digest_hex": actual,
        "passed": actual == expected,
        "evidence_type": "SOFTWARE_KNOWN_ANSWER_TEST",
    }


def simulate_board() -> dict[str, Any]:
    kat = known_answer_test()
    checks = [
        {"name": "software_sha256d_known_answer", "status": "PASS" if kat["passed"] else "FAIL"},
        {"name": "simulated_controller_protocol", "status": "PASS"},
        {"name": "simulated_chip_discovery", "status": "PASS"},
        {"name": "simulated_thermal_interlock", "status": "PASS"},
        {"name": "physical_board_present", "status": "NOT_VERIFIED"},
        {"name": "physical_chip_present", "status": "NOT_VERIFIED"},
        {"name": "live_pool_connection", "status": "NOT_RUN"},
        {"name": "accepted_pool_shares", "status": "NOT_RUN"},
    ]
    return {
        "schema": "brain-asic-board-simulation/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "unit_id": "BRAIN-ASIC-001",
        "status": "SIMULATION_PASS" if kat["passed"] else "SIMULATION_FAIL",
        "simulation_only": True,
        "physical_hardware_access": False,
        "fabrication_status": "NOT_PERFORMED",
        "board_presence": "NOT_VERIFIED",
        "chip_presence": "NOT_VERIFIED",
        "mining_status": "NOT_RUN",
        "measured_hashrate_hs": None,
        "measured_power_watts": None,
        "measured_temperature_c": None,
        "accepted_pool_shares": None,
        "simulated_telemetry": {
            "controller_state": "READY_SIMULATED",
            "chip_count": 1,
            "chip_state": "RESPONSIVE_SIMULATED",
            "thermal_interlock": "ARMED_SIMULATED",
            "power_rail_state": "NOMINAL_SIMULATED",
            "warning": "These are model states, not physical measurements.",
        },
        "known_answer_test": kat,
        "checks": checks,
        "limitations": [
            "This is a software model, not an ASIC emulator at RTL/gate/timing level.",
            "Simulated chip count and telemetry are illustrative only.",
            "No physical board or chip has been verified as received.",
            "No pool connection, mining work, accepted shares, payout, or profit is claimed.",
            "Do not use simulated voltage/current/temperature values to wire or power hardware.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    args = parser.parse_args()
    report = simulate_board()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"{report['unit_id']} — {report['status']}")
        print(f"Model: {report['model_id']}")
        print(f"SHA256d known-answer test: {'PASS' if report['known_answer_test']['passed'] else 'FAIL'}")
        print("Physical board/chip: NOT VERIFIED")
        print("Live mining: NOT RUN")
        print("All board telemetry is SIMULATED; this is not physical-device evidence.")
    return 0 if report["status"] == "SIMULATION_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

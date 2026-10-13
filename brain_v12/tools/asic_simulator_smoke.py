#!/usr/bin/env python3
"""Deterministic smoke test for Brain's software-only ASIC logic simulator.

Run from repository root:
    python brain_v12/tools/asic_simulator_smoke.py
This is a local simulator test, not proof of Render/MCP liveness or real hardware.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain_v12.brain.asic_hardware_simulator import (  # noqa: E402
    ASICLogicSimulator,
    ASICSimulationError,
    SIMULATOR_VERSION,
)

NETLIST = {
    "nodes": [
        {"name": "a", "op": "INPUT"},
        {"name": "b", "op": "INPUT"},
        {"name": "xor_out", "op": "XOR", "inputs": ["a", "b"]},
    ],
    "outputs": ["xor_out"],
}
VECTORS = [
    {"a": 0, "b": 0},
    {"a": 0, "b": 1},
    {"a": 1, "b": 0},
    {"a": 1, "b": 1},
]
EXPECTED = [0, 1, 1, 0]


def main() -> int:
    checks = []
    sim = ASICLogicSimulator(NETLIST)
    result = sim.run(VECTORS, max_cycles=4)
    actual = [cycle["outputs"]["xor_out"] for cycle in result["trace"]]
    checks.append({
        "name": "xor_truth_table",
        "pass": actual == EXPECTED,
        "expected": EXPECTED,
        "actual": actual,
        "cycles": result.get("cycles"),
    })

    bad_sim = ASICLogicSimulator(NETLIST)
    try:
        bad_sim.run(VECTORS, max_cycles=3)
        limit_rejected = False
    except ASICSimulationError as exc:
        limit_rejected = str(exc) == "CYCLE_LIMIT_EXCEEDED"
    checks.append({
        "name": "cycle_limit_enforced",
        "pass": limit_rejected,
        "expected_error": "CYCLE_LIMIT_EXCEEDED",
    })

    report = {
        "tool": "brain-asic-simulator-smoke",
        "simulator_version": SIMULATOR_VERSION,
        "scope": "local software simulation only",
        "real_hardware_measurement": False,
        "live_mcp_or_render_proof": False,
        "pass": all(item["pass"] for item in checks),
        "checks": checks,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

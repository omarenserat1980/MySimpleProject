#!/usr/bin/env python3
"""Repeatable software-only ASIC simulator microbenchmark.

Reports measured simulator cycles/s, node evaluations/s, and run latency
percentiles. Results characterize this Python environment only, not physical
ASIC throughput, clock rate, power, or mining revenue.
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain_v12.brain.asic_hardware_simulator import ASICLogicSimulator


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999999)))
    return ordered[index]


def make_netlist(gates: int) -> dict:
    nodes = [
        {"name": "a", "op": "INPUT"},
        {"name": "b", "op": "INPUT"},
        {"name": "g0", "op": "XOR", "inputs": ["a", "b"]},
    ]
    previous = "g0"
    operations = ("AND", "OR", "XOR", "NAND", "NOR", "XNOR")
    for i in range(1, gates):
        op = operations[i % len(operations)]
        nodes.append({"name": f"g{i}", "op": op, "inputs": [previous, "a"]})
        previous = f"g{i}"
    return {"nodes": nodes, "outputs": [previous]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=256, help="vectors per measured run")
    parser.add_argument("--repeats", type=int, default=30, help="number of measured runs")
    parser.add_argument("--gates", type=int, default=32, help="combinational gates in the chain")
    parser.add_argument("--seed", type=int, default=20261013, help="deterministic vector seed")
    args = parser.parse_args()
    if not 1 <= args.cycles <= 10000:
        parser.error("--cycles must be between 1 and 10000")
    if not 3 <= args.repeats <= 1000:
        parser.error("--repeats must be between 3 and 1000")
    if not 1 <= args.gates <= 500:
        parser.error("--gates must be between 1 and 500")

    rng = random.Random(args.seed)
    vectors = [{"a": rng.randrange(2), "b": rng.randrange(2)} for _ in range(args.cycles)]
    netlist = make_netlist(args.gates)
    durations = []
    for _ in range(args.repeats):
        simulator = ASICLogicSimulator(netlist)
        started = time.perf_counter()
        result = simulator.run(vectors)
        durations.append(time.perf_counter() - started)
        if not result.get("ok") or result.get("cycles") != args.cycles:
            raise RuntimeError("BENCHMARK_RUN_INVALID")

    total_cycles = args.cycles * args.repeats
    total_node_evaluations = total_cycles * len(netlist["nodes"])
    total_seconds = sum(durations)
    output = {
        "benchmark": "brain_asic_software_microbenchmark",
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor_label": platform.processor() or "not_reported",
        },
        "configuration": {
            "seed": args.seed,
            "cycles_per_run": args.cycles,
            "repeats": args.repeats,
            "gate_count": args.gates,
            "node_count": len(netlist["nodes"]),
        },
        "measurements": {
            "total_cycles": total_cycles,
            "total_node_evaluations": total_node_evaluations,
            "aggregate_cycles_per_second": total_cycles / total_seconds if total_seconds else 0,
            "aggregate_node_evaluations_per_second": total_node_evaluations / total_seconds if total_seconds else 0,
            "run_latency_seconds_median": statistics.median(durations),
            "run_latency_seconds_p95": percentile(durations, 0.95),
            "run_latency_seconds_min": min(durations),
            "run_latency_seconds_max": max(durations),
        },
        "interpretation": {
            "software_only": True,
            "physical_asic_performance_measured": False,
            "power_or_energy_measured": False,
            "revenue_measured": False,
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

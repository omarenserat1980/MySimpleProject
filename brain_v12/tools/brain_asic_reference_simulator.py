#!/usr/bin/env python3
"""Electronic Brain V12 software ASIC reference simulator and acceptance tests.

This is a deterministic software model, not silicon, FPGA, or physical-device
measurement. It emits reproducible vectors and machine-readable evidence.
No network calls, secrets, or cloud resources are required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Vector:
    name: str
    a: int
    b: int
    expected: int


def xor_gate(a: int, b: int) -> int:
    if a not in (0, 1) or b not in (0, 1):
        raise ValueError("digital inputs must be 0 or 1")
    return a ^ b


def half_adder(a: int, b: int) -> tuple[int, int]:
    """Return (sum, carry) for one-bit unsigned addition."""
    return xor_gate(a, b), a & b


def full_adder(a: int, b: int, carry_in: int) -> tuple[int, int]:
    if carry_in not in (0, 1):
        raise ValueError("carry_in must be 0 or 1")
    total = a + b + carry_in
    return total & 1, (total >> 1) & 1


def vectors() -> list[Vector]:
    return [
        Vector("xor_00", 0, 0, 0),
        Vector("xor_01", 0, 1, 1),
        Vector("xor_10", 1, 0, 1),
        Vector("xor_11", 1, 1, 0),
    ]


def run_acceptance(seed: int = 12013, random_cases: int = 256) -> dict:
    start = time.perf_counter_ns()
    failures: list[dict] = []
    checks = 0

    def check(name: str, expected: object, actual: object) -> None:
        nonlocal checks
        checks += 1
        if expected != actual:
            failures.append({"test": name, "expected": expected, "actual": actual})

    for v in vectors():
        check(v.name, v.expected, xor_gate(v.a, v.b))

    # Exhaustive half-adder and full-adder truth tables.
    for a in (0, 1):
        for b in (0, 1):
            check(f"half_sum_{a}{b}", (a + b) & 1, half_adder(a, b)[0])
            check(f"half_carry_{a}{b}", (a + b) >> 1, half_adder(a, b)[1])
            for cin in (0, 1):
                expected = (a + b + cin) & 1, (a + b + cin) >> 1
                check(f"full_adder_{a}{b}{cin}", expected, full_adder(a, b, cin))

    # Seeded property-style checks make runs reproducible.
    rng = random.Random(seed)
    for index in range(random_cases):
        a, b, cin = rng.randrange(2), rng.randrange(2), rng.randrange(2)
        check(f"property_full_adder_{index}", a + b + cin, sum(
            bit << shift for shift, bit in enumerate((*full_adder(a, b, cin),))
        ))
        # Independent arithmetic identity for XOR.
        check(f"property_xor_{index}", (a + b) % 2, xor_gate(a, b))

    elapsed_ns = time.perf_counter_ns() - start
    payload = {
        "schema_version": "1.0",
        "status": "PASS" if not failures else "FAIL",
        "model": "software-reference-digital-logic",
        "physical_hardware_tested": False,
        "network_used": False,
        "seed": seed,
        "random_cases": random_cases,
        "checks": checks,
        "failure_count": len(failures),
        "failures": failures,
        "elapsed_ns": elapsed_ns,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["evidence_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=12013)
    parser.add_argument("--random-cases", type=int, default=256)
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    if args.random_cases < 0 or args.random_cases > 100_000:
        parser.error("--random-cases must be between 0 and 100000")
    report = run_acceptance(args.seed, args.random_cases)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

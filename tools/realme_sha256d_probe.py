#!/usr/bin/env python3
"""Reproducible, non-mining SHA-256d probe for Android/Termux and other Python 3 hosts.

This verifies a known Bitcoin genesis-block header hash and reports a short
microbenchmark. It does not connect to a pool, search nonces, mine blocks,
or claim ASIC-equivalent performance.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import time
from pathlib import Path

EXPECTED_GENESIS_HASH = (
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
)
# Bitcoin genesis block header, serialized in wire format (80 bytes).
GENESIS_HEADER = bytes.fromhex(
    "01000000"
    + "00" * 32
    + bytes.fromhex(
        "4a5e1e4baab89f3a32518a88c31bc87f"
        "618f76673e2cc77ab2127b7afdeda33b"
    )[::-1].hex()
    + "29ab5f49"
    + "ffff001d"
    + "1dac2b7c"
)


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def read_memory_kib() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith(("MemTotal:", "MemAvailable:")):
                key, value, *_ = line.replace(":", "").split()
                values[key] = int(value)
    except (OSError, ValueError):
        pass
    return values


def read_thermal_millicelsius() -> list[int]:
    # Android exposes thermal-zone readings on some builds only. Read-only.
    readings: list[int] = []
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            raw = int(path.read_text().strip())
            if 0 < raw < 200_000:
                readings.append(raw)
        except (OSError, ValueError):
            continue
    return readings[:32]


def main() -> int:
    actual = sha256d(GENESIS_HEADER)[::-1].hex()
    iterations = max(1, min(int(os.environ.get("BRAIN_BENCH_ITERATIONS", "10000")), 1_000_000))
    started = time.perf_counter()
    for _ in range(iterations):
        sha256d(GENESIS_HEADER)
    elapsed = time.perf_counter() - started
    report = {
        "schema": "brain.realme.sha256d_probe.v1",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "header_bytes": len(GENESIS_HEADER),
        "expected_genesis_hash": EXPECTED_GENESIS_HASH,
        "actual_genesis_hash": actual,
        "reference_vector": "PASS" if actual == EXPECTED_GENESIS_HASH else "FAIL",
        "benchmark_iterations": iterations,
        "benchmark_elapsed_seconds": round(elapsed, 6),
        "sha256d_operations_per_second": round(iterations / elapsed, 2) if elapsed else None,
        "memory_kib": read_memory_kib(),
        "thermal_zone_readings_raw": read_thermal_millicelsius(),
        "thermal_reading_note": "Raw sysfs values only; units/device meaning may vary by Android build.",
        "scope": "Local software test only; not mining, pool acceptance, ASIC equivalence, power measurement, or revenue evidence.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["reference_vector"] == "PASS" and len(GENESIS_HEADER) == 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())

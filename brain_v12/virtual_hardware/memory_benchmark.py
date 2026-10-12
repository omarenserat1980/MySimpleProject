"""Deterministic virtual-memory workload; reports analytical estimates, not physical bandwidth."""
from __future__ import annotations

import hashlib
import json

from .memory import VirtualRAM


def run_memory_workload(profile_id: str, addresses: int = 1024, cache_enabled: bool = True) -> dict:
    if addresses < 1:
        raise ValueError("MEMORY_BENCHMARK_ADDRESSES_MUST_BE_POSITIVE")
    ram = VirtualRAM(addresses, profile_id=profile_id, cache_enabled=cache_enabled)
    vector = [(i, (i * 17 + 3) & 0xFFFF) for i in range(addresses)]
    digest = hashlib.sha256(json.dumps(vector, separators=(",", ":")).encode()).hexdigest()
    latency_ns = 0.0
    for address, value in vector:
        ram.write(address, value)
        latency_ns += ram.last_access_report.get("dram", {}).get("estimated_latency_ns", 0.0)
    checksum = 0
    for address, value in vector:
        checksum += ram.read(address)
        latency_ns += ram.last_access_report.get("dram", {}).get("estimated_latency_ns", 0.0)
    status = ram.status()
    bandwidth = status["dram_timing"]["peak_theoretical_bandwidth_bytes_per_second"]
    return {
        "benchmark": "brain-virtual-memory-read-write-v1",
        "profile_id": profile_id,
        "workload_sha256": digest,
        "addressable_cells_touched": addresses,
        "read_write_accesses": addresses * 2,
        "checksum": checksum,
        "estimated_latency_sum_ns": latency_ns,
        "analytical_peak_bandwidth_bytes_per_second": bandwidth,
        "host_payload_bytes_estimate": status["host_payload_bytes_estimate"],
        "host_rss_measured": False,
        "elapsed_host_seconds": None,
        "physical_bandwidth_measurement": False,
        "cache_hierarchy": status["cache_hierarchy"],
        "claim": "deterministic synthetic workload with analytical timing estimates only",
    }


if __name__ == "__main__":
    print(json.dumps(run_memory_workload("micron-ddr4-3200-x8"), indent=2, sort_keys=True))

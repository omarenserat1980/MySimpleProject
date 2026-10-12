"""Deterministic storage-model workload. Results are estimates, not physical measurements."""
from __future__ import annotations

import hashlib
import json

from .devices import VirtualStorage


def run_storage_workload_benchmark(profile_id: str, operations: int = 128,
                                   block_size_bytes: int = 4096, queue_depth: int = 1) -> dict:
    if operations < 1 or block_size_bytes < 1:
        raise ValueError("STORAGE_BENCHMARK_ARGUMENT_OUT_OF_RANGE")
    disk = VirtualStorage(profile_id=profile_id, queue_depth=queue_depth)
    descriptors = [{"op": "write", "path": f"/benchmark/block-{i}", "size": block_size_bytes}
                   for i in range(operations)]
    workload_hash = hashlib.sha256(json.dumps(descriptors, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    modeled_latency_us = 0.0
    total_bytes = 0
    for descriptor in descriptors:
        result = disk.write(descriptor["path"], bytes([descriptor["size"] % 251]) * block_size_bytes)
        modeled_latency_us += result["estimated_latency_us"]
        total_bytes += block_size_bytes
    telemetry = disk.smart_telemetry()
    return {
        "benchmark": "brain-virtual-storage-write-v1",
        "profile_id": profile_id,
        "fidelity": "timing_model",
        "workload_sha256": workload_hash,
        "operations": operations,
        "block_size_bytes": block_size_bytes,
        "queue_depth": queue_depth,
        "total_bytes": total_bytes,
        "estimated_latency_sum_us": modeled_latency_us,
        "estimated_iops": operations * 1_000_000 / max(1.0, modeled_latency_us),
        "vendor_sequential_write_max_bytes_per_second": disk.profile.sequential_write_bytes_per_second,
        "vendor_random_write_iops_qd1": disk.profile.random_write_iops_qd1,
        "vendor_random_write_iops_qd32": disk.profile.random_write_iops_qd32,
        "telemetry": telemetry,
        "elapsed_host_seconds": None,
        "physical_device_measurement": False,
        "claim": "deterministic model estimate compared with vendor reference limits; not a measured SSD benchmark",
    }


if __name__ == "__main__":
    print(json.dumps(run_storage_workload_benchmark("samsung-870-evo-1tb"), indent=2, sort_keys=True))

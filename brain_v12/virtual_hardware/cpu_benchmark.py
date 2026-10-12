"""Deterministic CPU interpreter workload; reports work counts, not physical speed."""
from __future__ import annotations

import hashlib
import json

from .x86_64 import X86_64CPU


def run_cpu_subset_benchmark(iterations: int = 1000, profile_id: str = "brain-x86-64-subset-v1") -> dict:
    if iterations < 1:
        raise ValueError("BENCHMARK_ITERATIONS_MUST_BE_POSITIVE")
    program = [("MOVI", "RAX", 0), ("MOVI", "RBX", 1)]
    program.extend(("ADD", "RAX", "RBX") for _ in range(iterations))
    program.append(("HLT",))
    workload_bytes = json.dumps(program, separators=(",", ":")).encode("utf-8")
    cpu = X86_64CPU(profile_id=profile_id)
    result = cpu.run(program, max_cycles=len(program) + 1)
    return {
        "benchmark": "brain-x86-symbolic-add-v1",
        "profile_id": profile_id,
        "fidelity": cpu.profile["fidelity"],
        "workload_sha256": hashlib.sha256(workload_bytes).hexdigest(),
        "requested_additions": iterations,
        "completed_interpreted_instructions": result["cycles"],
        "result_rax": result["registers"]["RAX"],
        "counter_semantics": result["counter_semantics"],
        "elapsed_host_seconds": None,
        "physical_cpu_performance_claim": False,
        "note": "Deterministic interpreter work-count benchmark; not IPC, physical cycles, or a host-performance measurement.",
    }


if __name__ == "__main__":
    print(json.dumps(run_cpu_subset_benchmark(), indent=2, sort_keys=True))

# Realme RMX3710 as the Brain ASIC Compute Substitute

## Decision

Designate the user's Realme RMX3710 Android phone, running Termux, as Electronic Brain's **physical edge compute node and software execution substitute** for ASIC-related development and experiments, within its measured capabilities.

This is an architecture decision; it does **not** classify the phone as a semiconductor ASIC or claim ASIC-equivalent performance.

## Responsibilities

- Use the phone for lightweight orchestration, local test execution, evidence collection, and bounded software workloads.
- Keep heavy RTL synthesis, physical-design flows, and cloud-scale jobs on available free CI runners or other explicitly authorized compute; do not assume the phone can run them efficiently.
- Treat the phone as a Thin Membrane client. Brain Cloud remains responsible for central orchestration, persistent memory, scheduling, analytics, and network management.
- Keep simulation, software hashing, RTL simulation, and Yosys synthesis evidence clearly labeled as software/CI evidence.
- Do not enable real mining, financial execution, purchases, or production-network changes as a consequence of this designation.

## Acceptance gates before claiming ASIC replacement

1. Record device model, Android/Termux environment, CPU architecture, available memory, thermal behavior, and power constraints.
2. Run reproducible SHA-256d reference tests on the phone and compare results against known-good vectors.
3. Benchmark throughput and energy only when reliable measurement is available; do not infer ASIC equivalence from a generic CPU benchmark.
4. For any pool integration, require explicit opt-in, safe test configuration, valid Stratum protocol behavior, and independently verifiable accepted-share evidence. No pool acceptance or payout is implied by local tests.
5. Keep hardware fabrication, silicon bring-up, and real revenue as separate unproven gates until independent evidence exists.

## Status

- **Architecture designation:** Realme RMX3710 = physical edge compute node / software ASIC substitute.
- **Dedicated ASIC silicon:** Not present or proven by this designation.
- **ASIC-equivalent performance:** Not established.
- **Real mining, accepted pool shares, and realized revenue:** Not established.

The purpose is to reuse the existing phone and preserve the zero-budget, simulation-first approach without misrepresenting software execution as dedicated ASIC hardware.

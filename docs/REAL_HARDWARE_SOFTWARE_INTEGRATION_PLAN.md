# Brain Real-Hardware Software Integration Plan

## Objective
Integrate established software projects into Electronic Brain hardware abstractions so simulated server, memory, CPU, storage, networking and ASIC components use real implementations where practical. Integration means invoking a pinned upstream tool, linking a documented adapter, or importing a license-compatible module—not copying a program into RAM or pretending software is physical hardware.

This is simulation-first. Software execution or simulation does not establish that physical RAM, an ASIC, a server, or a real Windows guest exists.

## Integration rules
1. Inventory the component contract, supported OS/architecture, dependencies, license, upstream release/commit, maintenance state and resource cost before import.
2. Pin a fixed upstream release/commit and record SHA-256. Verify signatures/checksums where available; a URL or checksum alone does not authenticate a publisher.
3. Review the exact version's license and notices before vendoring or redistributing. Prefer external tool invocation where possible. Do not copy proprietary firmware, drivers or vendor binaries.
4. Every adapter needs a Brain-owned interface, health probe, deterministic test fixture, timeout/resource limits and structured evidence. No secrets or host/network privileges by default.
5. Keep evidence levels separate: SIMULATED, TOOL_EXECUTED, RTL_SIMULATION_PASSED, SYNTHESIS_PASSED, HOST_INSPECTION_RECORDED and PHYSICAL_HARDWARE_VERIFIED require their own evidence.
6. Simulation and synthesis cannot create mining revenue, accepted pool shares or financial execution records.
7. Keep heavy toolchains off the Realme/Termux thin-membrane client unless explicitly needed. Use the phone as client/observation gateway; run heavy workloads on a capable authorized runner. Do not depend on low-RAM Arkan.

## Candidate integration matrix
These are candidates to evaluate, not tools already installed or integrated. Pin exact versions and review licensing/platform requirements before adoption.

| Brain component | Candidate upstream | Intended role | First acceptance evidence |
|---|---|---|---|
| Virtual server / VM | https://www.qemu.org/ | Disposable VM and host/guest evidence | Tool version, VM config fingerprint, guest-side evidence |
| CPU / system | https://www.gem5.org/ | Architectural CPU/system simulation | Pinned build, known workload, reproducible report |
| RAM / memory controller | https://github.com/CMU-SAFARI/ramulator2 | Memory-system simulation | Source/build pin, known trace, simulated latency/bandwidth report |
| DRAM timing alternative | https://github.com/umd-memsys/DRAMsim3 | Compare memory models | License/platform review, trace regression |
| RTL simulation | https://www.veripool.org/verilator/ and https://steveicarus.github.io/iverilog/ | Execute RTL testbenches | Compile/run logs and independent vectors |
| Logic synthesis | https://yosyshq.net/yosys/ | RTL-to-netlist synthesis | Tool/version, log, netlist hash, warnings review |
| ASIC physical design | https://theopenroadproject.org/ | Exploratory placement/routing with compatible open PDK | Pinned flow, PDK provenance, DRC/LVS where supported |
| FPGA/SoC framework | https://github.com/enjoy-digital/litex | Optional SoC/FPGA framework | Build manifest and simulation; board evidence needed for hardware claims |
| Storage | QEMU block devices + isolated host filesystem adapter | Virtual disks and reproducible storage tests | Image hash and read/write integrity test |
| Networking | Linux network namespaces / QEMU virtual networking | Isolated virtual NIC tests | Config fingerprint and virtual-peer test; no public-connectivity claim |
| Windows guest | QEMU + legally obtained Windows media | Disposable VM boot validation | Media digest, host inspection, guest-generated boot evidence and verifier result |

## Implementation sequence
### Stage 1 — Canonical inventory and adapter contracts
- Add a versioned registry with component, upstream URL, pin, license-review state, execution mode, evidence required and status.
- Each adapter exposes probe(), run_fixture(), collect_evidence() plus bounded timeout/resource settings.
- Unconfigured integrations default to NOT_CONFIGURED, never ready.

### Stage 2 — RAM and server simulation
- Initial adapter implemented: `brain_v12/hardware/ramulator_adapter.py`, with contract tests in `brain_v12/hardware/test_ramulator_adapter.py` and CI matrix registration.
- The adapter follows the upstream Ramulator 2.1 Python interface: it probes the installed Python package and runs a reviewed local `.py` example/configuration script, hashes the script, bounds execution time, and returns structured simulated-evidence. It does not install/download the upstream tool. Since these scripts are executable code, only reviewed scripts should run in an isolated runner.
- Next acceptance gate: CI must pass, then a pinned Ramulator 2.1 build and known example trace must run in an authorized runner with the tool version, config hash, trace identity and output artifact recorded.
- Keep model outputs separate from OS memory telemetry. A simulated 64 GiB configuration must never be reported as installed physical RAM.
- Integrate QEMU only after the runner has adequate resources and VM isolation.
- Keep model outputs separate from OS memory telemetry. A simulated 64 GiB configuration must never be reported as installed physical RAM.
- Integrate QEMU only after the runner has adequate resources and VM isolation.

### Stage 3 — ASIC toolchain
- Reuse existing brain_v12/asic RTL and CI path. Probe Icarus/Verilator/Yosys rather than silently pretending missing tools exist.
- Store tool versions, source pin, logs, test vectors, synthesized netlist hash and report hashes.
- RTL and synthesis passes remain distinct from fabricated-chip and pool-share evidence.

### Stage 4 — Other components
- Add storage, virtual networking, CPU/system simulation and OS guest adapters using the same contract.
- Each integration gets license notice, provenance manifest, smoke/regression tests, resource budget and rollback procedure.

## Current truth
This document is a plan, not evidence any candidate has been installed, built, executed or connected to physical hardware. Existing Brain ASIC work remains software/RTL simulation and synthesis until independently supported hardware bring-up evidence exists. Windows guest boot remains unverified until guest-side evidence is collected and validated.

## Done criteria for each adapter
- [ ] Exact upstream source/version pinned
- [ ] Adapter and contract tests implemented (Ramulator initial adapter exists; real upstream run still pending)
- [ ] License and redistribution decision recorded
- [ ] Reproducible build/invocation documented
- [ ] Resource and permission limits enforced
- [ ] Known-answer/regression test added
- [ ] Structured evidence and provenance emitted
- [ ] Failure and missing-tool cases fail closed
- [ ] CI reviewed before merge
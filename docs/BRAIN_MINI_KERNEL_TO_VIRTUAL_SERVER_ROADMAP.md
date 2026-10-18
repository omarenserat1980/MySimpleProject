# Brain Bottom-Up Digital Computer → Blade Server Roadmap

## Goal
Build a Brain-owned digital system incrementally, like assembling a machine from the simplest working component: digital clock → calculator → programmable CPU → computer → operating-system kernel → server → main server → blade-server fabric. Every layer must reuse and extend the verified layer below it.

**Truth boundary:** the initial milestones are software models and emulators. They do not, by themselves, create physical circuitry, reserve real CPU/RAM, implement Microsoft's Windows kernel, or prove a real Windows Server 2025 boot.

## Existing foundations — reuse rather than duplicate
- `brain_v12/virtual_hardware/kernel.py`: deterministic process lifecycle, timer ticks, syscall event log.
- `brain_v12/virtual_hardware/computer.py`: virtual CPU, RAM, storage, NIC, firmware, kernel, filesystem and bootloader composition.
- `brain_v12/virtual_hardware/cpu.py`, `x86_64.py`, `memory.py`, `bus.py`, `filesystem.py`, `firmware.py`, `bootloader.py`: existing computer building blocks.
- `brain_v12/virtual_hardware/server_fabric.py`: server profiles and explicit simulation/host-capacity boundaries.
- `brain_v12/brain/windows_server_2025_simulation_factory.py`: Windows Server 2025 behavior simulation and synthetic evidence.
- `brain_v12/web/windows-desktop-simulator.html`: browser desktop interface, not an operating system.

## Evolution ladder

### D0 — Digital clock and logic
- Define deterministic ticks, counters, Boolean operations, reset, and state transitions.
- Make timing logical/simulated; do not imply physical clock frequency.
- Acceptance: repeatable tests for increment, reset, rollover, and invalid inputs.

### D1 — Calculator
- Add arithmetic/logic operations over the existing logic primitives.
- Specify integer width, signedness, overflow, divide-by-zero, and result flags.
- Acceptance: table-driven tests for edge cases and deterministic results.

### D2 — Programmable mini-CPU
- Define a small versioned instruction set, registers, program counter, flags, and a bounded instruction-step loop.
- Load only BrainVM bytecode/program objects; no arbitrary host/native code execution.
- Acceptance: hand-written programs execute with exact expected register/memory snapshots and an instruction budget prevents infinite loops.

### D3 — Complete virtual computer
- Compose CPU + RAM + bus + storage + NIC + firmware + bootloader + filesystem using the existing `VirtualComputer`.
- Keep virtual memory and disk separate from host resources.
- Acceptance: boot sequence, read/write, CPU program, and virtual packet tests pass together.

### D4 — Mini-kernel and OS services
- Build on existing `VirtualKernel`: process lifecycle, timer scheduling, safe syscall allowlist, audit trail, and service manager.
- Unknown syscalls fail closed; no shell commands or native EXE execution.
- Acceptance: create → schedule → syscall → terminate tests; invalid tick and unknown PID tests pass.

### D5 — Standalone virtual server
- Add service dependency ordering, health checks, restart policy, virtual DNS/HTTP protocols, and loopback-only networking.
- Distinguish configured capacity from measured host CPU/RAM; external networking is disabled by default.
- Acceptance: deterministic API/service scenario plus injected-failure and recovery tests.

### D6 — Main server / controller
- Coordinate multiple virtual server nodes through the existing task queue and evidence systems.
- Add admission control, node identity, health/heartbeat timestamps, resource accounting, audit, snapshots, and recovery.
- Heartbeat or a stored record alone is not proof of remote reachability or current execution.
- Acceptance: multi-node tasks show traceable assignment, result, independent verification, and restart recovery.

### D7 — Blade-server fabric
- Model a chassis containing multiple independently identified blade nodes, management plane, virtual switch, shared-storage model, power/thermal telemetry model, and per-blade failure isolation.
- Reuse server fabric and virtual hardware components; do not duplicate schedulers or evidence stores.
- Acceptance: blade add/remove, isolated failure, rescheduling, and recovery tests; simulated chassis resources remain explicitly labelled `SIMULATED`.

### D8 — Optional real execution backend
- Only after simulation gates pass, evaluate a native/VM backend on authorized infrastructure.
- Require actual available compute/storage, explicit operator authorization, and independent host/guest evidence.
- Real Windows Server boot requires guest-generated evidence plus an independent completion gate. A green workflow, ISO, virtual profile, or simulated boot is insufficient.
- Do not make the low-memory Arkan laptop a required dependency or automatically create paid cloud resources.

## Windows Server relationship
Windows Server 2025 is a target behavior profile and optional guest OS, not the same thing as the Brain mini-kernel. Reuse `brain_v12/brain/windows_server_2025_simulation_factory.py`; keep reports labelled `execution_mode=SIMULATION_ONLY` and `real_windows_boot_verified=false` until independently proven otherwise.

## Evidence labels
- `SIMULATED`: model-generated state/capacity.
- `HOST_OBSERVED`: resource observation from a named host with timestamp.
- `GUEST_VERIFIED`: evidence generated inside the actual booted guest.
- Never promote a simulated value to host/guest truth without a verification gate.

## Current implementation status (simulation only)
- D0/D1: digital clock and mini-calculator primitives are implemented in `digital_logic.py`.
- D2: BrainVM instruction execution and a bounded execution board are implemented; checkpoint/resume is covered by focused tests.
- D4/D5 foundation: `BrainVMTaskRunner`, `BrainVirtualServerRuntime`, and `BrainVirtualHost` provide deterministic task/service models and serialized simulated state.
- D6 prototype: `BrainVirtualClusterManager` models ready/draining/failed nodes, round-robin placement, health summaries, and cluster checkpoint/restore.
- These are code-level milestones only. Do not mark the full D3–D7 acceptance gates complete solely because these abstractions exist.

## Immediate implementation target
Run the focused tests for the execution board, task runner checkpoint, virtual server, host, and cluster manager on the same PR revision. Fix failures before merge. Then add evidence-backed task placement/recovery integration tests and explicit resource accounting before progressing to the blade-server model. Do not start a parallel kernel or claim later stages complete before their acceptance tests pass.

# Brain Mini-Kernel → Virtual Server Roadmap

## Goal
Grow a very small, testable Brain-owned software kernel into a simulated server environment in small verified increments. This roadmap does **not** claim to implement Microsoft's Windows kernel or to boot Windows Server 2025.

## Existing foundations (reuse; do not duplicate)
- `brain_v12/virtual_hardware/kernel.py`: deterministic process lifecycle, timer ticks, syscall event log.
- `brain_v12/virtual_hardware/computer.py`: virtual CPU, RAM, storage, NIC, firmware, kernel, filesystem and bootloader composition.
- `brain_v12/virtual_hardware/server_fabric.py`: server profiles and simulation/host-capacity boundaries.
- `brain_v12/brain/windows_server_2025_simulation_factory.py`: Windows Server 2025 *behavior simulation* and synthetic evidence.
- `brain_v12/web/windows-desktop-simulator.html`: browser desktop interface; not an operating system.

## Incremental gates

### K0 — Mini-kernel contract (first milestone)
- Keep the kernel deterministic and side-effect-free.
- Test process create → timer scheduling → syscall audit → terminate.
- Reject negative timer ticks and unknown process IDs.
- Expose a stable status snapshot for later diagnostics.
- Never execute host commands or native Windows binaries.

**Acceptance:** focused unit tests pass; status explicitly labels this as simulated kernel behavior.

### K1 — Minimal kernel services
- Add a small, versioned syscall allowlist (status, monotonic tick, virtual file read/write only).
- Validate syscall names and arguments; reject unknown calls by default.
- Add tests for invalid inputs and audit-log behavior.

### K2 — Virtual boot chain
- Connect firmware → virtual bootloader → mini-kernel → init/service manager.
- Record ordered, deterministic boot events and failure reasons.
- Keep virtual disk contents separate from host files.

### K3 — Server services
- Add a virtual service manager with dependency ordering, restart policy, and health status.
- Add loopback-only virtual networking first; external networking remains disabled by default.
- Add DNS/HTTP-like protocol simulations without opening real sockets.

### K4 — Durable state and recovery
- Persist virtual machine configuration and synthetic run records in the existing Brain evidence store where supported.
- Test stop/restart/recovery and tamper detection.
- Distinguish stored reports from live liveness checks.

### K5 — Windows Server behavior profile
- Reuse the existing Windows Server 2025 simulation factory; do not build a second competing boot state machine.
- Model boot phases, service startup, network health, restart, and fault injection.
- Reports must retain `execution_mode=SIMULATION_ONLY` and `real_windows_boot_verified=false`.

### K6 — Optional real virtualization backend (separate approval gate)
- Only after the simulator is reliable, evaluate an isolated QEMU/KVM backend on an authorized host.
- Require available compute/storage, a legitimate OS installation source/license, explicit operator authorization, and guest-generated boot evidence.
- Do not use the low-memory Arkan laptop as a required execution dependency; do not create paid cloud resources automatically.
- A successful simulator run, green CI, ISO file, or QEMU process alone is not proof of a real Windows boot.

## Truth labels
- `SIMULATED`: model-generated state or capacity.
- `HOST_OBSERVED`: measured on a named host at a recorded time.
- `GUEST_VERIFIED`: evidence generated inside a booted guest.
- `real_windows_boot_verified` remains false until the independent real-boot gate passes.

## First implementation target
The first code change should strengthen tests around the existing `VirtualKernel`, not create a parallel kernel implementation. Only advance to K1 when K0 tests pass.

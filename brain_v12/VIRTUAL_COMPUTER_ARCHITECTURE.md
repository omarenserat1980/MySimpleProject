# Brain Virtual Computer / Blade Server Architecture

## Goal
The Brain owns a deterministic software-defined computer layer. Physical CPU, motherboard, modem, RAM and GPU are not required for the virtual machine to exist.

## Layers
Virtual Datacenter -> Blade Chassis -> Blade Server -> Virtual Computer -> CPU/RAM/Bus/Devices.

## Current implemented contract
- VirtualCPU: registers, program counter, arithmetic, memory load/store, jumps, output, halt and bounded cycle execution.
- VirtualRAM: bounded address space plus snapshot/restore.
- VirtualBus: device registry and interrupt event queue.
- VirtualStorage: bounded file store with SHA-256 manifest.
- VirtualNIC: deterministic send/receive queues.
- VirtualGPU: framebuffer and pixel operations.
- VirtualComputer: power state, boot count and device inventory.
- BladeServer: lifecycle and capability declaration.
- BladeScheduler: capability-based executor selection; it does not bind work to a fixed physical device.
- BrainVirtualDatacenter: provisioning and execution facade.

## Evidence gate
A Blade phase is not considered complete merely because Python imports succeed. Required evidence:
1. virtual computer boots;
2. CPU executes a program and produces the expected result;
3. scheduler selects a blade by capabilities;
4. scheduler refuses a missing capability;
5. all execution is bounded by a cycle limit;
6. state/status is inspectable.

## Next layers
1. Virtual firmware/bootloader.
2. Virtual kernel/process model.
3. Interrupt controller and timers.
4. Virtual filesystem and persistent disk image.
5. Virtual modem/router/IP stack.
6. Virtual GPU command queue.
7. Blade health/heartbeat/lease and failure recovery.
8. Durable scheduler and artifact/evidence store.
9. Multi-blade networking and service discovery.
10. Optional physical adapters; the virtual machine remains functional without them.

## Principle
The virtual computer is an internal Brain subsystem, not a replacement claim for physical electronics. It can execute software and model hardware deterministically, while real internet, radio and physical I/O require an explicit adapter.

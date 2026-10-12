# Brain virtual hardware profile foundation

## Purpose

The virtual computer already has a deterministic educational CPU, addressable-cell RAM, a device registry/bus, in-memory storage, a packet-buffer NIC, and a software framebuffer. This layer describes those existing behaviors explicitly; it does not replace them with a parallel simulator.

## Fidelity contract

- **functional**: modeled operations and state transitions are implemented and testable.
- **timing_model**: timing is estimated from explicit parameters; this does not imply exact microarchitectural timing.
- **cycle_accurate**: every relevant modeled event is matched at cycle granularity against a specified reference model. This label must not be used without appropriate evidence.

Each profile records modeled behaviors, unsupported features, provenance, and conformance-test identifiers. Starter profiles are explicitly **synthetic baselines**, not real vendor models. Replace their provenance and parameters with authoritative vendor documentation and/or measured hardware traces before making claims about a specific physical part.

## Current model boundaries

- CPU: 8-register educational ISA (`MOVI`, `ADD`, `SUB`, `LOAD`, `STORE`, `JMP`, `JZ`, `OUT`, `HALT`); not x86-64 or AArch64.
- RAM: integer-valued addressable cells with bounds checking and snapshot/restore; values are not restricted to 8-bit bytes, so capacity is reported in cells, not guaranteed byte-accurate RAM. This is not a DDR4/DDR5 timing or ECC model.
- Bus: deterministic device registry and recorded interrupt events; not PCIe transaction or electrical signaling emulation.
- Storage: bounded in-memory byte objects; not NVMe controller timing, physical SSD behavior, or power-loss durability.
- Network: packet buffers; not a complete Ethernet PHY/MAC or wire-time model.
- GPU: software framebuffer; not CUDA/Vulkan/DirectX execution or GPU compute acceleration.

## Timing and machine manifests

`ClockModel` converts modeled cycles and seconds using a deterministic ideal frequency. `MachineManifest` validates component inventory and reports per-component fidelity. Profile validation does not allocate host RAM/CPU, boot an operating system, or prove equivalence with physical hardware.

## Verification

Run:

```bash
python -m unittest brain_v12.tests.test_hardware_profiles -v
```

Future increments should add bus arbitration and DMA semantics, interrupt delivery contracts, memory hierarchy/cache timing, storage/network latency distributions, power/thermal estimates, and reference-driven conformance tests. Each increment must declare unsupported behavior and must not label estimated telemetry as physical measurement.

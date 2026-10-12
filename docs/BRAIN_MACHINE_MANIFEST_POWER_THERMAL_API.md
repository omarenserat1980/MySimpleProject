# Integrated VirtualComputer manifest, power/thermal estimates, and lifecycle API

## Versioned machine manifest

`VirtualComputer.hardware_manifest()` now emits schema version 2. The manifest contains CPU, RAM, cache (when enabled), motherboard/topology, bus, GPU, storage, NIC, firmware, power, and thermal components. Each component reports a profile identifier, fidelity level, modeled behavior, unsupported features, provenance/source references, parameters, and inferred or explicit units. `validate_configuration()` checks the manifest and bus topology before `power_on()`.

The default motherboard is a **synthetic** PCIe Gen4 x24 topology profile, not a commercial motherboard. It is intentionally a software model; lane budgeting can reject combinations that exceed the selected topology. Machine creation does not allocate physical devices or host capacity matching the declared simulated capacity.

## Power and thermal model

`PowerThermalModel` implements a deterministic lumped thermal-RC estimate, configurable ambient temperature, thermal inertia, cooling coefficient, fan curve, throttling, shutdown threshold, and cooling/sensor/power-interruption fault injection. It supports explicit simulated time steps and recovery after load reduction. All temperatures and watts are estimates. Default idle/peak watts and thermal parameters are synthetic assumptions; known vendor TDP references are listed separately and are not summed as a complete system power measurement.

## Checkpoint/recovery

`VirtualComputer.checkpoint()` emits a JSON-safe, checksummed snapshot of CPU subset state, sparse RAM, virtual storage current/durable data, NIC queues, framebuffer/logical VRAM state, bus events, and thermal state. `restore_checkpoint()` verifies checksum, machine identity, and configuration fingerprint before restoring state; the machine remains powered off and must be booted again. Kernel process tables/open handles and host/external device state are explicitly not restored. Checkpoint data contains in-memory virtual disk payloads, not a host disk image.

## API

The FastAPI router is registered at `/api/virtual-hardware`:

- `GET /profiles` — profile catalog (read-only)
- `POST /machines` — create and validate a virtual machine
- `GET /machines` and `GET /machines/{id}` — list/status
- `GET /machines/{id}/manifest` — versioned manifest
- `POST /machines/{id}/boot`, `/workloads`, `/benchmark`, `/thermal/advance`, `/checkpoint`, `/restore`, `/shutdown` — lifecycle operations

Mutating/status routes require the existing Brain control-key authentication. The machine registry is process-local, so callers must persist checkpoint objects externally for restart recovery. Benchmark output never claims physical CPU/GPU performance; it reports deterministic emulator work counts and explicitly omits host elapsed time.

## Verification

Run `python -m unittest brain_v12.tests.test_machine_manifest -v`. Tests cover manifest contents/units, boot validation, deterministic thermal response and cooling recovery, thermal faults, checkpoint integrity/recovery, and API route registration.

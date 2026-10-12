# Electronic Brain — Extended Virtual Peripheral Fabric

## Purpose

This increment adds software-only models for peripheral categories not yet represented by the core `VirtualComputer` composition. It is additive: it does not replace the existing CPU, RAM/cache, motherboard/bus, GPU, NIC, storage, firmware, kernel, bootloader, power, thermal, or fault-injection implementations.

Module: `brain_v12/virtual_hardware/extended_devices.py`

Composition entry point: `VirtualPeripheralFabric`

## Included models

| Device family | Model behavior | Explicit boundary |
|---|---|---|
| TPM-like measurement | PCR-style hash extension and deterministic quote digest | No hardware-backed key, vendor TPM command engine, or hardware attestation |
| USB controller | Port allocation, class checks, attach/detach inventory | No USB electrical signaling, host passthrough, or full USB protocol |
| Serial console | Bounded line buffer and read window | No physical UART or host serial port |
| Watchdog | Arm/feed/tick/expiry state machine | Expiry reports an event; it does not reset the host or VM |
| RNG | Seeded reproducible byte stream | Test RNG only; never cryptographic entropy |
| Cellular modem | Power, registration, APN, signal estimate, connect and byte accounting | No radio, SIM/network operator, external transmission, or Internet gateway |
| BMC | Estimated temperature/fan telemetry, PSU health, event log | No IPMI implementation, physical sensors, or real power control |
| IOMMU | Per-device DMA region allow-list | Software check only; no hardware isolation guarantee |
| RAID | RAID 0/1/5/10 logical capacity and member availability/degraded status | No block I/O, parity/rebuild execution, persistence, or data redundancy |
| Battery | State-of-charge and energy estimate | No calibrated electrochemistry or measured watts |
| Keyboard/mouse/touch | Bounded event queue | No host input capture |
| Audio | Sample-rate/channel/frame accounting | No audio rendering, codec, or host sound output |
| Sensor hub | Named numeric estimates | Values are uncalibrated and synthetic |

## Example

```python
from brain_v12.virtual_hardware.extended_devices import VirtualPeripheralFabric

fabric = VirtualPeripheralFabric()
fabric.tpm.extend(0, "brain-bootloader-v1")
fabric.usb.attach(1, "keyboard-0", "hid")
fabric.watchdog.arm()
fabric.modem.power(True)
fabric.modem.register("brain.test")
fabric.modem.connect()
assert fabric.modem.transmit(b"simulated payload")["external_transmission"] is False
print(fabric.inventory())
```

## Fidelity and safety rules

- Default mode is `SIMULATED`; no physical hardware is required.
- The models do not open host devices, allocate host resources, execute vendor firmware, or enable external networking.
- The modem records simulated byte counts only.
- TPM-like quote output is an integrity digest, not a signed hardware attestation.
- The RNG is deterministic and explicitly not cryptographically secure.
- RAID reports logical capacity/health; it does not store data or claim durability.
- Power, temperature, fan, voltage, battery, timing, and capacity values are estimates or configured model inputs unless an independent calibration source is added.
- `VirtualComputer` now creates the extended fabric and includes its inventory/status in machine status and the versioned hardware manifest. This does not claim device-specific boot firmware or guest driver support.
- Extended peripheral runtime state is not yet included in machine checkpoint/restore; restart persistence must not be assumed.

## Verification

Focused tests are in `brain_v12/tests/test_extended_virtual_devices.py`. Run:

```bash
python -m unittest brain_v12.tests.test_extended_virtual_devices -v
```

A successful code commit or pull-request creation is not itself evidence that CI passed. Merge only after the focused test and required GitHub Actions checks pass, and review integration with existing virtual hardware first.


## PCIe transaction-level model

Module: `brain_v12/virtual_hardware/pcie.py`

The virtual bus now owns a `VirtualPCIeFabric` instance and exposes configuration-space and BAR/MMIO operations. Non-CPU/RAM devices attached to the bus receive deterministic virtual BDFs and synthetic BARs; no host MMIO range is mapped.

Modeled behavior:
- BDF endpoint enumeration and basic 256-byte PCI configuration header fields.
- Vendor/device/class identifiers, command/status registers, synthetic BAR discovery.
- Sparse little-endian BAR memory with aligned 1/2/4/8-byte MMIO reads and writes.
- Bounded transaction trace, modeled completion latency by configured link generation, counters, and deterministic timeout/drop/error injection.
- Failed transport completions do not mutate MMIO state.
- The bus status and hardware manifest expose PCIe generation, endpoint count, transaction statistics, and explicit fidelity boundaries.

Not modeled: bit-accurate TLP/DLLP framing and CRC/replay, link training/electrical signaling, cycle-accurate arbitration, real host BAR mapping, physical IOMMU enforcement, vendor device firmware, or real hardware hot-plug.

Example:

```python
from brain_v12.virtual_hardware import VirtualBus

bus = VirtualBus()
bus.attach("gpu0", object())
bus.config_read("gpu0", 0, 2)       # synthetic vendor ID
bus.mmio_write("gpu0", 0, 0, 0x1234)
assert bus.mmio_read("gpu0", 0, 0)["value"] == 0x1234
```

Focused tests: `python -m unittest brain_v12.tests.test_virtual_pcie -v`.

The transaction-level PCIe addition increases functional device-bus fidelity, but it is not cycle-accurate or electrical emulation and must not be interpreted as a single overall hardware-emulation percentage.

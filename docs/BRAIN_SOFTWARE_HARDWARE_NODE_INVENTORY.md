# Electronic Brain — Preliminary Software Hardware Nodes

## Goal

Create an initial software node for every component referenced by every device family in `device_catalog.py`, plus a node template for every networking device kind. This is the complete **initial inventory/node layer**, not a claim that all physical devices are already functionally emulated.

## Module

- `brain_v12/virtual_hardware/software_hardware_nodes.py`
- `SoftwareHardwareNodeFabric` creates deterministic IDs in the forms `device.<family>.<component>` and `network.<kind>`.
- Every node has a type, family, component identity, model binding/fidelity label, lifecycle state, enable/disable controls, dependency references, and explicit no-physical-I/O flags.
- Existing CPU/RAM/GPU/NIC/storage/PCIe/power/network models are referenced rather than duplicated. Unimplemented pieces are labeled as catalog contracts rather than falsely represented as full emulation.

## Scope

Includes every component listed in each of the device catalog's families: computers, laptops, servers, phones/tablets, consoles, networking appliances, storage, displays, media devices, wearables, smart-home devices, office equipment, vehicles, medical/scientific devices, robotics/industrial control, energy systems, peripherals, space systems, and embedded/IoT. The network catalog's router, switches, firewall, wireless, WAN, DNS/DHCP, load balancing, storage fabrics, and other network-device kinds are also represented.

## Fidelity and boundaries

- `CATALOGED` means a node identity is available, not that the component is fully emulated.
- Existing adapters have only their documented fidelity: for example, PCIe is transaction-level, power/thermal is estimated, and modem/radio nodes are isolated state models.
- Vendor-specific firmware, exact commercial SKU parameters, electrical/PHY signaling, and full guest-driver compatibility remain separate work.
- No host hardware, host sockets, radio transmission, or external I/O is enabled.

## Verification

Run:

```bash
python -m unittest brain_v12.tests.test_software_hardware_nodes -v
```

The tests assert coverage of every catalog family/component pair and every networking device class, stable node IDs, dependency validation, and the software-only boundary.

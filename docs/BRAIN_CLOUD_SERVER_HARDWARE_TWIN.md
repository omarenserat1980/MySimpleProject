# Brain Cloud Server — Complete Hardware Twin

## Purpose
Define a server hardware twin that models the complete observable hardware surface of a modern x86-64 cloud/server machine without claiming that simulated capacity is physical capacity.

## Hardware domains

### Chassis and physical plant
- chassis identity, form factor, rack position, sled/blade identity
- motherboard, sockets, DIMM slots, PCIe slots, M.2/U.2/U.3 bays
- hot-swap bays, backplane, risers
- power supplies, redundancy mode, input power, power budget
- fans, fan curves, pumps, coolant loop, heatsinks, thermal zones
- temperature, voltage, current, power, fan RPM and intrusion sensors

### Management plane
- BMC identity and firmware
- IPMI/Redfish-style management model
- serial console, KVM, virtual media
- power cycle, reset, boot override
- watchdog and management network
- health/telemetry/event log

### Compute
- CPU sockets and package identity
- cores, threads, SMT, frequency/P-states, C-states
- cache hierarchy, TLB model
- NUMA nodes and CPU affinity
- memory controllers and memory channels
- ISA/features and microcode identity
- interrupt controllers, timers and APIC topology

### Memory
- DIMMs, ranks, banks, channels
- capacity, speed, ECC
- memory-controller attachment
- NUMA locality
- reserved/available/allocated capacity
- ECC error counters and health
- memory pressure and throttling state

### Expansion and I/O
- PCIe root complexes, bridges and switches
- bus/device/function addressing
- BAR/MMIO regions
- MSI/MSI-X and IRQ routing
- DMA
- IOMMU groups
- SR-IOV virtual functions
- USB controllers/devices
- SATA/SAS/HBA controllers
- serial/console devices

### Storage
- NVMe controllers and namespaces
- SATA/SAS disks
- SSD/HDD identity and health
- queues, IOPS, throughput and latency characteristics
- RAID controllers and arrays
- logical volumes
- filesystem/block-layer abstractions
- snapshots and thin provisioning
- SMART/health telemetry

### Network
- physical NICs
- ports, MACs and PHY state
- link speed/duplex/autonegotiation
- VLANs, bonds/teams and bridges
- SR-IOV VFs
- virtual NICs
- queues, RSS, interrupts and offloads
- packet counters, errors and link health
- management network vs data network

### Accelerators
- discrete GPU/accelerator devices
- memory/HBM
- compute engines
- device-local topology
- PCIe/NVLink-like fabric representation
- partitioning/MIG-like logical slices where applicable
- accelerator health and temperature

### Firmware/platform
- UEFI firmware
- Secure Boot
- TPM 2.0
- SMBIOS/DMI
- ACPI tables and power states
- boot order and boot entries
- platform UUID/serial identity
- firmware versions
- microcode identity
- NVRAM variables
- RTC/clock

### Virtualization
- Hyper-V/KVM/QEMU backend contracts
- vCPU topology
- vNUMA
- virtual memory
- virtual PCIe
- virtual disks
- virtual NICs
- vTPM
- virtual firmware
- snapshots/checkpoints
- passthrough and mediated devices
- live migration capability/constraints

## Cross-cutting truth model
Every component has: identity + topology + capacity + allocation + state + health + telemetry + lease + owner + fencing_epoch + evidence + backend + cost + limits + fallback

States include: UNKNOWN, PRESENT, AVAILABLE, RESERVED, ATTACHED, RUNNING, DEGRADED, OFFLINE, FAULTED, STALE, RECOVERING, QUARANTINED, BLOCKED

## Physical truth boundary
The twin may model arbitrary capacity, but execution admission must distinguish:
- SIMULATED: model only
- PROVISIONED: requested but not yet verified
- VERIFIED: backed by measured/attested real resources
- ATTACHED: bound to an execution backend
- RUNNING: backend confirms active execution

A virtual 1 TB memory device is therefore not equivalent to 1 TB of physical RAM.

## Canonical execution path
Mission -> Capability Graph -> Hardware Twin -> Resource Fabric -> Capacity Gate -> Execution Kernel -> Backend -> Worker -> Evidence -> Verify

## Backends
- Hyper-V on Windows
- QEMU/KVM on Linux
- container/host resource execution
- real cloud VM/bare-metal provider
- distributed worker pools

The twin remains provider-neutral; the backend owns actual hardware realization.

## Non-goals
This model does not claim to emulate transistor-level CPU behavior, analog power electronics, electrical signaling, or every vendor-specific microarchitectural implementation. Such fidelity would require a hardware simulator and vendor models. The goal is complete server-level resource/topology/control-plane coverage with explicit fidelity boundaries.
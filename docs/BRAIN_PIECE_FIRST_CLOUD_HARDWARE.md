# BRAIN PIECE-FIRST CLOUD HARDWARE

## Decision
The cloud server is a graph of independent software-defined hardware pieces. The server is a projection of those pieces and their connections, not the fundamental object.

## Independent pieces
Each piece has: piece_id, type, domain, parent, children, connections, provider, backend, identity, capacity, allocatable_capacity, capabilities, state, health, telemetry, lease, owner, fencing_epoch, evidence, cost, limits and fallback.

Core domains:
- power: PSU, power bus, controller
- cooling: fan, pump, thermal controller, sensors
- management: BMC, management NIC, console, KVM, watchdog
- compute: CPU socket, core, thread, cache, NUMA, memory controller, interrupt controller, timer
- memory: DIMM, channel, bank, ECC controller
- I/O: PCIe root/switch/bridge, IOMMU, DMA, IRQ/MSI
- storage: NVMe controller, namespace, SSD, RAID, volume, filesystem
- network: NIC, port, PHY, queue, RSS, VLAN, bridge, vSwitch
- accelerator: GPU, GPU memory, compute engine, accelerator partition
- platform: UEFI, Secure Boot, TPM, ACPI, SMBIOS, RTC

## First-class connections
A connection is an independent object with connection_id, source, target, type, direction, capacity, allocation, latency, bandwidth, state, health, protocol, backend and evidence.

Connection types include POWER, THERMAL, PCIe, MEMORY, NUMA, DMA, IRQ, NETWORK, STORAGE, CONTROL, MANAGEMENT, SECURITY, CLOCK and FIRMWARE.

## Graph model
HardwareGraph = (Pieces, Connections).
The graph must answer which CPU connects to which NUMA node, which GPU to which PCIe root, which PSU powers which board, which NIC reaches which switch, and what alternate path exists after a failure.

## Piece lifecycle
DECLARED -> DISCOVERED -> PROVISIONED -> VERIFIED -> CONNECTED -> AVAILABLE -> RESERVED -> ATTACHED -> ACTIVE.
Independent failure states: DEGRADED, STALE, OFFLINE, FAULTED, QUARANTINED, RECOVERING.

A failed fan does not automatically make the whole server offline. Its effects propagate through the cooling connections and can reduce CPU allocatable capacity.

## Truth and realization
A piece may be realized by REAL_HARDWARE, HYPER_V, QEMU, KVM, CONTAINER, CLOUD_VM, CLOUD_SERVICE, SOFTWARE_EMULATION or SIMULATION.
Every piece exposes realization, truth state and evidence. Software may model a GPU, but must not claim physical GPU capacity without verification.

## Capacity rules
Distinguish PHYSICAL, DERIVED, VIRTUAL, ALLOCATABLE, RESERVED and ATTACHED capacity.
Never double-count CPU package, NUMA, cores and threads. Every allocatable capacity has a canonical owner/source.

## Graph-based admission
The planner requests a required subgraph rather than a generic server: CPU >= N, memory >= N, storage >= N, NIC >= N, TPM/security capability, plus required power, thermal and control paths.

Flow:
MISSION -> CAPABILITIES -> PIECE REQUIREMENTS -> PIECE DISCOVERY -> CONNECTION PLANNING -> COMPATIBILITY CHECK -> RESERVE PIECES -> RESERVE CONNECTIONS -> ATTACH -> VERIFY GRAPH -> EXECUTE.

## Compatibility gate
A connection is accepted only when capability compatibility, capacity, topology, security, valid evidence, lease and fencing conditions pass.

## Failure propagation
Failure propagates through graph edges. Example: FAN failure -> cooling path degraded -> thermal zone affected -> CPU health degraded -> CPU allocatable capacity reduced -> Resource Fabric refresh -> scheduler avoids affected CPU.

## Replacement
Pieces can be replaced independently. A failed DIMM can be quarantined and replaced while the machine identity remains stable. The component identity changes, and the new piece must be rediscovered and verified.

## Graph verification
A machine is RUNNABLE only when every required piece is VERIFIED or ATTACHED, every required connection is CONNECTED, required capacity is available, no blocking health state exists, and evidence is valid.

## Architecture
ChatGPT -> Mission Control -> Capability Graph -> Piece Requirements -> Hardware Graph -> Truth/Evidence -> Resource Fabric -> Capacity Gate -> Execution Kernel -> Backend -> Worker -> Telemetry -> Reconciler -> Graph Repair -> Recovery.

## Non-negotiable truth rule
Brain must never claim that a server has a resource without being able to identify the exact pieces, connections, provider, backend, capacity, state, health, evidence, observation time, owner, lease, fencing epoch and fallback.
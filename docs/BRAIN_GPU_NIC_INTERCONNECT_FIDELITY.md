# Virtual GPU, NIC, and motherboard/interconnect profiles

## Reference profiles

- **NVIDIA Tesla T4**: 40 streaming multiprocessors, 2,560 CUDA cores, 320 Tensor Cores, 16 GB GDDR6, up to 320 GB/s memory bandwidth, 8.1 TFLOPS FP32 peak, PCIe Gen3 x16, 70 W. Source: NVIDIA T4 product brief linked in `peripheral_profiles.py`.
- **Intel Ethernet Controller I225-V**: single 2.5 GbE port, PCIe x1 Gen2, 1.95 W, jumbo frames supported. Source: Intel product specifications linked in `peripheral_profiles.py`.
- **Brain synthetic motherboard topologies**: Gen4 x24 and Gen3 x20 total-lane budgets, with four SATA ports. These are software topology profiles, not named commercial motherboards. PCIe generation reference links are provided, but lane totals are explicit simulator assumptions.

## GPU model

`VirtualGPU` preserves the framebuffer API and optionally adds logical VRAM quota, transfer estimates, bounded command queue, synchronization, and synthetic FP32 workload estimates. Selecting Tesla T4 provides reference parameters only: no CUDA-compatible API, driver, physical VRAM, or real GPU execution is present. VRAM capacity is metadata and does not allocate 16 GB of host or GPU memory.

## NIC model

`VirtualNIC` preserves `send`, `inject`, and `receive` compatibility. A selected Intel I225-V profile adds MTU checks, bounded TX/RX queues, backpressure, modeled serialization latency, interrupt moderation, and virtual-bus DMA accounting. External networking remains disabled. Requesting it fails closed until a separately reviewed network adapter is implemented; packets are not sent to the host network.

## Motherboard and interconnect

`VirtualBus` can select a synthetic topology, allocate PCIe lanes, negotiate device link generations, enforce total lane/SATA-port budgets, estimate link bandwidth, enumerate devices, record DMA transfers, route interrupt events, and model virtual reset/hot-plug. A profile such as Gen4 x24 can accommodate T4 x16 + NVMe x4 + I225-V x1 (21 total lanes). Gen3 x20 rejects that same combination before boot because it would require 21 lanes.

DMA is an accounting/timing event; payload bytes are not physically DMA-copied. Interrupts are recorded events, not architectural interrupt delivery. No PCIe TLP/DLLP protocol, electrical signal fidelity, IOMMU hardware enforcement, real hot-plug signaling, or actual external networking is implemented.

## Power and performance claims

GPU and NIC wattages are vendor reference values, not measured consumption. GPU throughput and network latency are estimates, not benchmarks from physical devices. The models never claim hardware acceleration.

## Tests

Run `python -m unittest brain_v12.tests.test_peripheral_profiles -v`. Tests cover sourced profile metadata, logical VRAM, deterministic work estimates, command queue backpressure, MTU/packet queue behavior, topology lane conflicts, DMA accounting, interrupts, and fault isolation.

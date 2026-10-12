# Virtual RAM, DRAM timing profiles, and cache hierarchy

## Source-backed DRAM references

- `micron-ddr4-3200-x8`: Micron MT40A2G8JC-062E:E reference component, 16 Gb, x8, 3200 MT/s, CL22, 1.2 V.
- `micron-ddr5-5600-x16`: Micron MT60B1G16HC-56B:G reference component, 16 Gb, x16, 5600 MT/s, CL46, 1.1 V.
- `micron-lpddr5x-8533-x64`: Micron MT62F768M64D4CZ-023-AUT:C reference component, 48 Gb, x64, 8533 MT/s, 0.5 V. CAS latency is programmable and not specified as one fixed value in this profile.

Manufacturer links and source notes are embedded in `memory_profiles.py`. Channel count and 64-bit system channel width are configurable platform assumptions; they are not inferred from a single memory component. Peak bandwidth is an analytical upper bound: MT/s × modeled channel width × channel count ÷ 8. CAS timing is estimated from the selected CAS cycles and transfer rate. Missing tRCD/tRP/tRAS values are not invented.

## Sparse virtual RAM

`VirtualRAM` keeps a logical addressable-cell capacity while storing only nonzero cells in a sparse dictionary. Declaring billions of addressable cells therefore does not create a list with billions of entries. The compatibility `_data` view remains list-like for ordinary indexing, while resource accounting uses `used_cells` rather than scanning every logical cell. Cell values remain Python integers for compatibility; this is not a byte-exact DRAM model. RAM snapshots preserve the legacy `{size, nonzero}` shape.

Host payload byte estimates cover integer payload magnitudes only; they are not process RSS measurements and exclude Python object/dictionary overhead. `host_rss_measured` is always false.

## Cache hierarchy

Optional `CacheHierarchy` models L1/L2/L3 tags using deterministic set-associative LRU replacement. Its sizes and hit latencies are explicitly synthetic defaults, not asserted specifications for Intel/AMD CPU profiles. It stores tags only, not cached data, and does not model cache coherence, prefetch, false sharing, or cycle-accurate arbitration. CPU LOAD/STORE operations through `VirtualRAM` can update the timing and cache counters when enabled; the CPU instruction counter remains an interpreter work count.

## Memory timing and contention

`MemoryTimingModel` calculates estimated CAS/transfer latency and theoretical bandwidth, tracks outstanding requests, and reports same-bank contention. For LPDDR5X, the default 32-cycle CAS value is a simulator assumption unless overridden; it is not a Micron default. The model does not implement the full DRAM command protocol, PHY training, refresh scheduling, ECC signaling, or measured physical latency/bandwidth.

## Verification

Run `python -m unittest brain_v12.tests.test_memory_hierarchy -v`. Tests cover sourced profile values, analytical bandwidth, sparse capacity, boundaries, snapshot compatibility, cache hit/miss behavior, timing queue contention, and integration with VirtualComputer, ResourceManager, and BladeServer.

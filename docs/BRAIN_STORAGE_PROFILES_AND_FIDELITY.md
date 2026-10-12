# Virtual SSD profiles, timing estimates, and durability boundaries

`VirtualStorage` retains its original in-memory file API and adds selectable reference profiles:

- **Samsung 870 EVO 1TB SATA**: SATA 6 Gb/s, up to 560 MB/s sequential read and 530 MB/s write, QD1/QD32 IOPS, 2 GB DRAM cache, 600 TBW endurance rating.
- **Samsung 990 PRO 1TB NVMe**: PCIe Gen 4.0 x4 / NVMe 2.0, up to 7,450 MB/s read and 6,900 MB/s write, QD1/QD32 IOPS, 1 GB DRAM cache, 600 TBW endurance rating.

Sources are the manufacturers' datasheets linked in `storage_profiles.py`. Vendor maxima are reference specifications under vendor test conditions; they are not values measured by this simulator.

## Implemented model

- Logical capacity is metadata; declaring a 1 TB virtual device does not allocate a 1 TB host file or buffer.
- Existing `write`, `read`, and `manifest` calls remain supported. Virtual paths are normalized and `..`, NUL, and backslash path forms are rejected.
- Optional profiles select modeled queue limits, deterministic latency estimates, throughput limits, QD1/QD32 IOPS reference points, write-back cache semantics, `flush`, logical `trim`, SMART-style counters, endurance estimates, and deterministic timeout/reset/power-loss fault injection.
- Published QD1 and QD32 IOPS are source points. Intermediate configured queue depths use linear interpolation and are an explicit approximation.
- Profiled storage defaults to write-back semantics: call `flush()` to commit the in-memory durability snapshot. `restart()` discards unflushed changes. Unprofiled storage preserves legacy write-through behavior.
- `host_disk_allocation_bytes` is always zero because this implementation is memory-backed only. It does not open host files, raw block devices, or create disk images.

## Unsupported / not claimed

No NVMe command-set implementation, SATA controller protocol, real SMART protocol, NAND/FTL behavior, physical cache durability, real TRIM erasure, controller firmware timing, or measured physical-device performance is implemented. Latency is estimated from vendor throughput/IOPS points, not a measured latency distribution. File-backed temporary images and physical-device adapters are not implemented; no host block-device write path exists.

## Tests

Run `python -m unittest brain_v12.tests.test_storage_profiles -v`. Tests cover vendor profile provenance, compatibility, logical quota/path containment, queue depth, deterministic estimates, flush/restart durability, logical TRIM, telemetry, and injected faults.

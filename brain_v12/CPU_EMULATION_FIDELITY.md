# Electronic Brain CPU emulation fidelity

## Scope
VirtualCPU is a deterministic BrainVM-1 tuple interpreter for MOVI, ADD, SUB, LOAD, STORE, JMP, JZ, OUT, and HALT. It does not decode x86-64 or ARM machine-code bytes.

## Reference profiles
- `brainvm-baseline`: synthetic BrainVM baseline.
- `intel-core-i7-12700k-reference`: [Intel processor specifications](https://www.intel.com/content/www/us/en/products/sku/134599/intel-core-i712700k-processor-25m-cache-up-to-5-00-ghz/specifications.html).
- `amd-epyc-9654-reference`: [AMD EPYC 9654](https://www.amd.com/en/products/cpu/amd-epyc-9654).

Profile clocks and cache sizes are reference/model inputs, not vendor-calibrated performance claims.

## Fidelity boundaries
- Functional ISA: BrainVM-1 tuple operations only.
- Registers: eight Python integers, without fixed hardware width.
- Flags: zero, negative, carry and overflow metadata; not complete native ISA semantics.
- Decode: tuple dispatch only; no x86/ARM byte decoder.
- Exceptions: program counter, register bounds, RAM bounds, illegal opcodes and cycle limit.
- Privilege modes, native interrupts, pipeline behavior, cache eviction/coherence, TLB and cycle-accurate timing are not modeled.
- Cache counters and estimated cycles are transparent deterministic estimates, not measurements.

A profile named after a physical CPU is provenance metadata only; it does not mean that CPU's native instructions run in BrainVM.

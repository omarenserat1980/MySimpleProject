# Electronic Brain CPU emulation fidelity

## Scope
`VirtualCPU` remains the backwards-compatible deterministic BrainVM-1 tuple interpreter: `MOVI, ADD, SUB, LOAD, STORE, JMP, JZ, OUT, HALT`. It does not decode x86-64 or ARM machine-code bytes.

## Reference profiles
- `brainvm-baseline`: synthetic baseline.
- `intel-core-i7-12700k-reference`: [Intel Core i7-12700K specifications](https://www.intel.com/content/www/us/en/products/sku/134599/intel-core-i712700k-processor-25m-cache-up-to-5-00-ghz/specifications.html), [Intel Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html).
- `amd-epyc-9654-reference`: [AMD EPYC 9654](https://www.amd.com/en/products/cpu/amd-epyc-9654).

Use `VirtualCPU(profile_name="...")` or `cpu.select_profile("...")`. Processor names and links are provenance/reference metadata. They do not activate the native ISA. The configured clock and cache cost parameters are model inputs, not physical measurements or vendor-calibrated latency.

## Fidelity boundaries
- Functional ISA: BrainVM-1 tuple operations only.
- Registers: eight Python integer values; they have no fixed hardware width.
- Flags: zero/negative/carry/overflow metadata; not complete native ISA flag semantics.
- Decoding: tuple dispatch only; no x86/ARM byte decoder.
- Exceptions: bounded PC/cycle, invalid register, RAM bounds and unsupported opcode errors.
- Privilege modes: not modeled.
- Interrupts: VirtualBus can queue events; CPU delivery and interrupt frames are not implemented.
- Pipeline: not modeled; each tuple executes atomically.
- L1/L2/L3: deterministic cache-line presence approximation for LOAD/STORE; no eviction policy, associativity, coherence, prefetch, TLB or calibration.
- Timing: `cycles` counts retired BrainVM tuples. `estimated_cycles` adds simplified memory costs. Neither is cycle-accurate CPU performance.
- Native x86-64 / AArch64: NOT IMPLEMENTED by this class. The separate `X86_64CPU` remains a limited interpreter subset, not complete x86-64 emulation.

## Verification
Run `python -m unittest brain_v12.test_cpu_emulation -v`. These tests verify the declared BrainVM contract, not vendor conformance. Record profile, program, host Python and run conditions when comparing benchmarks. Host elapsed time measures the Python runtime, not emulated silicon.

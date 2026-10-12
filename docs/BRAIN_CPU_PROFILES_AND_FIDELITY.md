# CPU profiles and fidelity contract

`brain_v12/virtual_hardware/cpu_profiles.py` supplies selectable reference profiles for the existing symbolic `X86_64CPU` interpreter. Real hardware entries use official Intel/AMD specification URLs and record model parameters, but selection does not activate or claim a matching microarchitecture.

## Profiles

- `brain-x86-64-subset-v1`: symbolic tuple interpreter compatibility profile.
- `intel-core-i7-6700`: reference metadata (4 cores, 8 threads, 3.4 GHz base, up to 4.0 GHz, 8 MiB Intel Smart Cache, 65 W TDP) from Intel product documentation.
- `amd-ryzen-5-5600`: reference metadata (6 cores, 12 threads, 3.5 GHz base, up to 4.4 GHz boost, 384 KiB L1, 3 MiB L2, 32 MiB L3, 65 W TDP) from AMD product documentation.

## Fidelity boundary

`X86_64CPU` consumes symbolic instruction tuples. It does not decode x86 machine-code bytes and is not a complete x86-64 implementation. Its `cycles` counter is an interpreted-instruction count, not a hardware cycle measurement. Real profiles currently select reference metadata while running the same subset; pipeline, cache timing, SMT, privilege rings, paging, architectural interrupt delivery, SIMD, floating point, and microarchitecture-specific behavior remain unsupported. Interrupt requests are queued and explicitly reported as not delivered.

The subset tracks selected arithmetic flags (CF/PF/AF/ZF/SF/OF), 64-bit wraparound, and structured unsupported-opcode reports. These are reference-driven subset tests, not proof of whole-ISA conformance.

## References

- Intel, *Intel 64 and IA-32 Architectures Software Developer Manuals*: https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- Intel Core i7-6700 specifications: https://www.intel.com/content/www/us/en/products/sku/88196/intel-core-i76700-processor-8m-cache-up-to-4-00-ghz.html
- AMD, *AMD64 Architecture Programmer's Manual, Volumes 1-5*: https://docs.amd.com/v/u/en-US/40332_4.09_APM_PUB
- AMD Ryzen 5 5600 specifications: https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-5-5600.html

## Verification

Run `python -m unittest brain_v12.tests.test_cpu_profiles -v`. For deterministic instruction-count comparisons use fixed symbolic workloads and report the count as interpreter work only; do not label it physical IPC, cycles, or benchmark performance.

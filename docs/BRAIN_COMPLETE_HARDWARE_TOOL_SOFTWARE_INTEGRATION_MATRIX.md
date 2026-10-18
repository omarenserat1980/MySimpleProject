# Brain Complete Hardware, Tool and Software Integration Matrix

## Purpose

This is the canonical execution backlog for integrating upstream software with Electronic Brain. It is an inventory and acceptance contract, not a claim that every listed tool is installed or has run. Keep the evidence level for each row explicit.

## Integration contract

Every adapter must provide:
- probe(): detect an installed/available dependency without installing it or exposing secrets.
- run_fixture(): execute a reviewed, deterministic fixture under bounded time/resource limits when safe.
- collect_evidence(): record exact upstream revision/version, license/notice review, command, input/config hashes, exit status, bounded logs and output hashes.
- Fail-closed states for missing tools, unsupported host, timeout, failed assertions or missing evidence.
- A documented permissions boundary and rollback path.
- Independent evidence before promoting any claim to physical hardware, live mining, accepted shares or revenue.

## Inventory

| Brain subsystem | Real upstream candidate(s) | Integration mode | Minimum acceptance evidence | Current gate |
|---|---|---|---|---|
| RAM / DRAM timing | [Ramulator 2](https://github.com/CMU-SAFARI/ramulator2), [DRAMsim3](https://github.com/umd-memsys/DRAMsim3) | External source build + trace/config adapter | Immutable source revision, license review, build/run logs, trace/config hash, checked latency/bandwidth output | Pinned Ramulator 2 upstream revision built and example executed with expected-output assertions in GitHub Actions run 39149941417; simulation only. Next: connect a reviewed Brain memory trace |
| CPU / system architecture | [gem5](https://www.gem5.org/) | Pinned simulator build + known workload | Revision, binary version, workload ID/hash, reproducible output | Candidate |
| VM / server | [QEMU](https://www.qemu.org/) + KVM where supported | Read-only host preflight then disposable guest | Host capability record, VM config fingerprint, guest-generated boot evidence | Preflight adapter exists; target host and guest boot unverified |
| Windows Server guest | QEMU + legally obtained Microsoft media | Isolated disposable VM | Media provenance/hash, read-only host inspection, guest-side boot evidence | Blocked until authorized media and capable runner |
| RTL simulation | [Verilator](https://www.veripool.org/verilator/), [Icarus Verilog](https://steveicarus.github.io/iverilog/) | Compile and run Brain RTL testbench | Tool versions, compile/run logs, independent SHA-256d vectors, artifact hashes | Existing CI varies by runner; upstream tool execution must be individually evidenced |
| Logic synthesis | [Yosys](https://yosyshq.net/yosys/) | RTL synthesis | Version, synthesis logs, netlist hash, warnings and timing review | Candidate/CI-dependent |
| ASIC physical design | [OpenROAD](https://theopenroadproject.org/) + compatible open PDK | Isolated flow | Toolchain and PDK provenance, flow logs, DRC/LVS reports, output hashes | Blocked for physical claims; design-flow evidence not fabrication |
| FPGA / SoC | [LiteX](https://github.com/enjoy-digital/litex) | Optional SoC generation/simulation | Pinned dependencies, generated design hash, simulation; board identity for hardware claims | Candidate |
| Storage | QEMU block tools + isolated filesystem tooling | Temporary image, integrity and read/write fixture | Image hash, round-trip checks, no writes outside workspace | Planned |
| Virtual networking | Linux network namespaces / QEMU virtual networking | Isolated virtual peer test | Topology/config hash, packet/peer test logs | Planned; not proof of public connectivity |
| GPU / accelerator | Vendor-neutral runtime probes; CUDA/ROCm only where runner supports them | Detect-first optional adapter | Device/driver identity from authorized runner, tool version, known workload | Not configured until a capable runner is observed |
| Thermal sensors | OS sensor interfaces and device-specific I²C/SPI drivers | Read-only sensor adapter | Sensor model/identity, bus read, units, calibration and freshness | Blocked without identified physical sensor |
| Power / cooling | Device-specific telemetry and calibrated instruments | Read-only monitoring | Instrument identity, calibration, device identity, timestamped readings | Blocked for physical measurements |
| Mining algorithm / ASIC RTL | Brain SHA-256d RTL + Verilator/Icarus/Yosys | Known-answer tests, simulation and synthesis | Independent vectors, tool versions, logs, netlist hash | Software/RTL evidence only; not a fabricated ASIC |
| Mining pool client | Authorized upstream pool protocol/client implementation | Dry-run first; live execution separately gated | Pool endpoint/config redaction, accepted-share records from pool, device identity | No real accepted shares established by adapter presence |
| Revenue / payouts | Read-only pool telemetry and independent payout/blockchain evidence | Reconciliation only; never infer from hashrate estimates | Accepted-share records, payout transaction, independent reconciliation | Blocked until real evidence exists |
| Video/media engine | [FFmpeg](https://ffmpeg.org/) + ffprobe | External tool invocation | Version, input/output hashes, probe report, QC assertions | Existing media health abstraction; verify exact runtime per runner |
| Git and CI execution | Git + GitHub Actions; Brain-native runner remains separate | Repository operations, isolated workflow runner | Commit SHA, job logs, artifact manifests, permissions audit | CI runs are software evidence only |
| YouTube publishing | Official YouTube Data API / OAuth | Authenticated adapter; explicit publish gate | Scope verification, dry-run validation, returned video ID/status | Credentials and live publish must be independently configured |
| Device bridge / Termux | Brain Device Bridge + device-side runtime | Thin client / observation gateway | Device identity, authenticated heartbeat, command allowlist, signed execution receipt | Phone is not a substitute for cloud compute or ASIC |
| Security / secrets | OS environment or dedicated secret store | Least-privilege secret injection | Redaction tests, access policy, rotation audit; never emit secret values | No secrets in Git; no secret output in evidence |
| Monitoring / recovery | Brain supervisor + OS health probes | Read-only diagnostics then policy-limited recovery | Health check result, action audit, before/after evidence | Recovery actions must be bounded and authorized |
| Income/opportunity engine | Public market/source adapters and Brain decision gates | Read-only data first | Source timestamp, freshness, provenance and independent financial gate | Opportunity estimates are not realized revenue |

## Execution order

1. Ramulator 2 upstream execution is verified for pinned revision `c6c7a5de0cef35935d6fad7369e6271406798865` (GitHub Actions run 39149941417). Next, add a reviewed representative Brain memory trace and deterministic regression; outputs remain simulation-only.
2. Make ASIC toolchain evidence reproducible: detect and pin Verilator/Icarus/Yosys; run known SHA-256d vectors and store logs/netlist hashes.
3. Run host preflight on an authorized capable runner: QEMU/KVM tools and available memory; never assume the user's low-RAM PC is suitable.
4. Integrate CPU/system, storage and virtual networking using disposable fixtures and resource budgets.
5. Add optional GPU, thermal and power adapters only when the corresponding runner/device actually exists.
6. Keep publishing and mining execution behind separate explicit authorization gates. No purchases, paid infrastructure, secret creation, or live financial execution by default.

## Status vocabulary

- NOT_CONFIGURED: no usable runtime detected.
- ADAPTER_IMPLEMENTED: Brain adapter and tests exist; upstream execution not established.
- TOOL_EXECUTION_VERIFIED: an identified upstream version actually ran and generated retained evidence.
- SIMULATION_VERIFIED: known fixture assertions passed; still not physical hardware.
- HOST_EVIDENCE_RECORDED: authorized host or guest emitted independently checked evidence.
- PHYSICAL_HARDWARE_VERIFIED: independent, device-specific evidence supports the claim.
- BLOCKED: missing prerequisites or evidence.

Never promote status from source links, mocked tests, configuration declarations, simulated hashrate or green unrelated CI. This inventory is complete as a working integration backlog, not a claim that every possible future Brain tool has been discovered.

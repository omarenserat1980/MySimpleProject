# Electronic Brain — Simulation-to-Real Execution and Hardware Roadmap

**Status:** planning and evidence map; this document does not claim that physical hardware exists.  
**Baseline commit reviewed:** `e33dff13a42e967d872ea9c421537885c2cde735`  
**Budget rule:** zero-cost tools and hosted CI first. No purchases, paid provisioning, foundry orders, production changes, or secrets changes are authorized by this plan.

## 1. Objective

Move every simulator-backed capability toward the strongest real execution layer that is technically appropriate, while retaining simulation as a safe fallback and keeping the evidence types distinct.

"Real" has four different meanings and must never be collapsed into one status:

1. **Real software execution:** a real process runs on an identified CPU/OS or cloud host.
2. **Real digital implementation:** synthesizable RTL is tested with an actual RTL simulator and synthesis tool, producing inspectable netlists and reports.
3. **Real programmable hardware:** the design is programmed onto a physical FPGA/dev board and exercised with observed I/O, clocks, power and device identity.
4. **Real custom silicon:** a foundry accepts the process-specific tapeout, manufactures and packages the die, and traceable laboratory tests verify the physical device.

A simulator PASS is not a substitute for any higher gate. GDSII output is a layout artifact, not proof of fabrication. A connected mining pool is not proof of accepted shares; accepted shares are not proof of a payout; a payout is not proof of net profit.

## 2. Repository baseline discovered

The repository already has substantial foundations:

- `brain_v12/asic/rtl/`: synthesizable RTL and testbenches, including SHA-256/Bitcoin proof-of-work modules and the Brain datapath.
- `brain_v12/asic/digital_lab.py`: RTL simulation and Yosys synthesis/evidence path.
- `brain_v12/asic/execute_asic_pipeline.py`: local tool discovery and bounded simulation/synthesis runner.
- `brain_v12/asic/toolchain_probe.py`: read-only probe for Icarus Verilog, Verilator and Yosys.
- `brain_v12/asic/openroad/` and `.github/workflows/asic-rtl-to-gds.yml`: OpenROAD/SKY130 physical-design experiment.
- `brain_v12/asic/hardware/ASSEMBLY_PLAN.md` and `BOM.csv`: preliminary physical prototype plan and unassessed bill of materials.
- `brain_v12/brain/asic_hardware_simulator.py`: ideal two-state software logic simulator; explicitly not a physical ASIC or transistor-level model.
- `brain_v12/brain/sha256d_execution_contract.py` and `sha256d_rtl_adapter.py`: shared, fail-closed evidence contract and RTL adapter.
- `brain_v12/brain/bitcoin_pool_evidence.py`, `bitcoin_stratum_evidence.py`, and related mining gates: separate external pool/mining evidence path.
- Virtual/cloud/device/Windows simulators exist elsewhere in `brain_v12/brain/` and `brain_v12/virtual_hardware/`.

This means the next task is not to create another disconnected simulator. It is to connect these existing layers through a common capability registry, evidence schema, acceptance gates and hardware adapters, then run each gate and record the result.

## 3. Conversion matrix

| Existing simulation / component | First real execution target | Physical target when applicable | Required proof before status can advance |
|---|---|---|---|
| ASIC logic simulator | Icarus Verilog or Verilator executing the same truth tables/test vectors | FPGA fabric, then custom ASIC only if justified | Differential vectors, tool/version, exit code, marker, source hashes; then board identity and measured I/O |
| Bitcoin SHA-256d / nonce search | RTL simulation plus independent CPU reference vectors | FPGA prototype for digital feasibility; mining ASIC is a separate design-scale effort | Golden vectors, target/endianness checks, nonce boundary tests, synthesis report, hardware-vs-reference comparison |
| RTL source | Lint, formal/property checks where feasible, real RTL simulation | FPGA synthesis/programming, or ASIC synthesis | Exact RTL revision, constraints, tool versions, logs and output hashes |
| Synthesized netlist | Yosys netlist and structural checks | FPGA bitstream or ASIC mapped netlist | No latches/unsupported cells where prohibited, warnings reviewed, mapped cell/library provenance |
| OpenROAD/GDSII | Reproducible RTL-to-GDS flow and artifact retention | Foundry-qualified tapeout and packaged silicon | Process-specific DRC/LVS/ERC/antenna/density/timing/power signoff, accepted submission, fabrication and lab evidence |
| Software hardware/virtual nodes | Real process on a known host; report OS, CPU architecture, resource limits | Real host, VM, or device with attested identity | Heartbeat, authenticated identity, command allowlist, logs, timestamps; do not infer physical hardware from simulated inventory |
| Windows Server/VM simulator | Actual authorized VM or host boot | Real machine only if required | Provider/host identity, guest boot evidence, guest-side nonce/challenge and service health; simulator output is insufficient |
| Network/API simulator | Real authenticated endpoint in a bounded, read-only probe | Actual network device only if the feature requires it | TLS/identity checks, request/response IDs, timestamped logs, no secret disclosure |
| Termux/device bridge simulator | Actual agent process on the Android device | Phone hardware itself | Device heartbeat, authenticated agent identity, capabilities, OS/arch, bounded command receipt and execution evidence |
| Mining pool/Stratum simulator or probe | Actual authorized pool connection | ASIC/FPGA/CPU worker with measured hashrate | Real worker ID, accepted share/job evidence, timestamps, server response; separate pool activity from payout |
| Revenue/payment simulator | Sandbox first, then provider-verified production events only after authorization | Not a hardware stage | Signed/order-bound provider event, idempotent reconciliation, settlement/payout evidence, fees and net balance |
| Media/video simulator | Real encoder process and generated media validation | Device/GPU acceleration only if available | ffmpeg/ffprobe version, artifact hash, decode/QC results, measured resource use |
| Cloud resource simulator | Actual free/authorized runner or host executing a task | Cloud VM/physical server if genuinely provisioned | Provider execution ID, actual job logs and resource report; no inference from estimated capacity |

Some simulated entities are logical services, not physical components. Do not force a cloud, payment, or media service into an ASIC/FPGA pathway; connect it to the real execution adapter appropriate to its function.

## 4. Canonical layered architecture

Every component should expose the same lifecycle:

`DISCOVER -> CLASSIFY -> PREFLIGHT -> EXECUTE -> OBSERVE -> VERIFY -> ACCEPT_OR_BLOCK`

- **Registry:** stable component ID, source path, intended capability, execution adapters, dependencies and evidence policy.
- **Adapters:** `SIMULATOR`, `HOST_SOFTWARE`, `RTL_TOOLCHAIN`, `FPGA_DEVICE`, `PHYSICAL_ASIC`, `REMOTE_SERVICE`. Adapters must declare their scope honestly.
- **Shared contract:** `NOT_RUN`, `PASS`, `FAIL`, `BLOCKED`, `TIMEOUT`, `CANCELLED`; status never upgrades without the exact evidence required by that layer.
- **Evidence store:** source revision, tool/device identity, tool versions, command or test ID, start/end timestamps, exit status, logs, artifact SHA-256, raw measurements, limitations and verifier.
- **Independent verifier:** validate evidence from raw artifacts or device/provider observations, not merely a self-reported boolean from the component under test.
- **UI:** show simulation, software execution, digital RTL, FPGA, ASIC layout, fabricated silicon, pool activity and realized revenue as separate statuses.

A digest detects accidental changes; it is not a digital signature or proof of who generated the evidence. Device attestations require a defined trust root and verified signatures.

## 5. ASIC/FPGA gate sequence

### Gate A — Requirements and source identity
- Identify the exact function to convert, I/O, clock, throughput, memory, interfaces, power/thermal limits and acceptance tests.
- Pin source commit and RTL hashes. Identify which modules are genuinely synthesizable.
- Keep simulation as the reference implementation; add a known-answer test suite.

### Gate B — Digital correctness
- Run Icarus Verilog/Verilator using explicit tool versions.
- Compare RTL outputs against an independent CPU/reference implementation over fixed vectors and randomized bounded tests.
- Test resets, cycle boundaries, timeout/cancellation, invalid inputs, nonce boundaries, endianness, target comparison and error paths.
- Add formal assertions/property checking where practical; a passing testbench alone is not formal proof.

### Gate C — Synthesis and implementation estimates
- Run Yosys and preserve the mapped/netlist outputs and reports.
- For FPGA, use the chosen vendor/toolchain's synthesis and timing reports; do not assume a generic Yosys estimate equals the final board's timing.
- For ASIC, pin the process design kit (PDK), standard-cell library, timing corners and constraints. Review area, timing, power assumptions and warnings.
- Never label estimated power/throughput as measured hardware data.

### Gate D — Physical FPGA prototype
- First confirm that a compatible board is already available or that the user explicitly approves acquiring one. Do not buy or provision anything under this plan.
- Check device part number, I/O voltage, clock, power input, thermal envelope, programming interface and licensing/tool compatibility against the official board/device documentation.
- Build a reproducible bitstream; record bitstream hash, synthesis/timing reports, board/device ID and firmware/tool versions.
- Exercise known-answer vectors on the board and compare observed outputs with the CPU/RTL reference. Capture actual I/O/clock evidence using appropriate instruments or trusted on-board instrumentation.
- Only then mark the FPGA gate PASS. An FPGA is a real programmable digital prototype, not a custom ASIC and not automatically a competitive Bitcoin miner.

### Gate E — ASIC physical design
- Complete a pinned RTL-to-GDS flow and retain the GDS/OASIS, mapped netlist, constraints, timing/power reports and tool/PDK identities.
- Run process-specific signoff checks required by the chosen foundry: DRC, LVS, ERC, antenna, density/fill, extraction, timing and power. A generic structure check or zero router violations does not replace foundry signoff.
- Compare die area and expected performance against the actual target workload. SHA-256d mining requires a fully validated, high-throughput architecture; a small demonstration core is not a production mining ASIC.

### Gate F — Fabrication, package and silicon
- Require explicit human approval and a confirmed budget before any paid shuttle, manufacturing, packaging, shipping or lab service.
- Verify foundry/shuttle identity, official submission rules, accepted package and written acceptance.
- Mark `FABRICATED` only after independent foundry/manufacturing evidence. Mark `SILICON_TESTED` only after traceable physical-device tests, device serial/lot identity, test setup, raw results and repeatability evidence.

### Gate G — Real mining and realized economics
- Keep mining disabled until an actual authorized worker and its safety/thermal/power constraints are established.
- Validate the pool endpoint, protocol, worker identity, jobs, shares and server responses. Do not equate TCP connection or submitted shares with accepted shares.
- Require accepted-share evidence and independent pool-side worker/hashrate evidence before declaring active pool mining.
- Require independently verifiable payout/settlement evidence before declaring revenue. Report gross revenue, fees, electricity, hosting, hardware/fabrication cost, and net result separately.
- Never claim that simulation, an RTL pass, GDSII, or a hashrate estimate generated money.

## 6. Priority order for this repository

1. **P0 — Consolidate, don't duplicate:** inventory the existing simulators and adapters; make one registry the source of truth and link each component to its current evidence gate.
2. **P1 — Make the digital reference reproducible:** run the current RTL/CPU SHA-256d differential tests, save artifacts and pin the exact commit/toolchain. Keep the ideal Python ASIC simulator labeled as a simulator.
3. **P2 — Prove synthesis quality:** run Yosys checks, inspect inferred cells/latches and warnings, and record area/timing estimates with explicit assumptions.
4. **P3 — Physical-design evidence:** re-run the pinned OpenROAD/SKY130 flow on the exact current source; archive the GDS hash and complete reports. Re-check the existing PR/branch for the physical-flow experiment before creating new code.
5. **P4 — FPGA decision gate:** inventory hardware already available, then choose an FPGA target only after compatibility and cost are known. If no board is available and the budget remains zero, keep this gate BLOCKED and continue software verification.
6. **P5 — ASIC foundry gate:** complete process-specific signoff and seek a zero-cost/explicitly sponsored shuttle only if genuinely available. No foundry or fabrication status until independently confirmed.
7. **P6 — External operations:** connect physical-device evidence to pool-side mining evidence and then to settlement/revenue reconciliation.

## 7. Required evidence manifest fields

Each gate should produce a machine-readable record containing:

- `schema_version`, `component_id`, `stage_id`, `status`, `execution_scope`
- `source_commit`, `source_hashes`, `tool_versions`, `device_or_provider_identity` (when applicable)
- `started_at_utc`, `finished_at_utc`, `command_or_test_id`, `exit_code`
- `artifact_paths`, `artifact_sha256`, `raw_measurements`, `verification_method`
- `limitations`, `blocked_reasons`, `reviewer_or_independent_verifier`
- Explicit false-by-default claims for `physical_hardware_verified`, `fabrication_verified`, `pool_share_accepted`, `payout_verified` and `revenue_verified`.

Evidence is incomplete if required fields are missing. Do not accept a claimed status from a screenshot alone when raw machine-readable evidence or provider-side verification is available.

## 8. Acceptance criteria for this roadmap

- Every simulator has an owner, intended real execution target, adapter, evidence contract and next gate.
- The UI never mixes simulated hardware with a real device, FPGA, fabricated ASIC, pool worker or revenue status.
- Missing tools, missing devices, expired credentials, timeouts and absent evidence produce `BLOCKED`/failure, never fabricated success.
- No new secrets, paid resources, production settings, external mining jobs or fabrication orders are created by CI.
- The physical ASIC gate stays blocked until process-specific signoff and independent manufacturing evidence exist.
- The real mining gate stays blocked until independent pool-side evidence exists; revenue stays blocked until independently verifiable settlement evidence exists.

## 9. Public technical references

- OpenROAD documentation: https://openroad.readthedocs.io/en/latest/main/README.html
- OpenROAD project and RTL-to-GDSII overview: https://openroad.org/
- OpenLane repository (notes that OpenLane 1.x is in maintenance and points new projects to LibreLane): https://github.com/The-OpenROAD-Project/OpenLane
- cocotb documentation (Python-based verification of Verilog/VHDL RTL using a simulator): https://docs.cocotb.org/
- Icarus Verilog: https://github.com/steveicarus/iverilog
- Yosys: https://github.com/YosysHQ/yosys

This roadmap is an engineering plan and evidence policy, not proof that any FPGA board, ASIC, foundry submission, mining worker, payout, or revenue currently exists.

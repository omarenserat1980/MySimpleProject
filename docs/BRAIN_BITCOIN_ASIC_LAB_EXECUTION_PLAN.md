# Brain Bitcoin ASIC Lab — Execution Plan

**Project:** Electronic Brain V12/V13  
**Repository:** `omarenserat1980/MySimpleProject`  
**Default branch:** `main`  
**Execution policy:** zero initial budget (0 JOD), open-source/free tools first, no paid cloud mining, no automatic purchases, and no physical-device assumptions.

## 1. Objective

Build an evidence-driven engineering path from a reproducible Bitcoin SHA-256 proof-of-work reference implementation to an RTL candidate, reproducible simulation and synthesis, optional physical-design artifacts, and—only if hardware and operating funds are later explicitly approved—a real miner connected to a pool.

This plan does **not** claim that Bitcoin can be minted arbitrarily, that an RTL design is a manufactured ASIC, or that simulation is real mining or income.

## 2. Existing baseline and integration

- The existing ASIC directory is `brain_v12/asic/`; its README identifies the RTL as a prototype and separates software simulation, RTL simulation, synthesis, FPGA execution, and silicon validation.
- Preserve the existing `brain_v12/asic/rtl/brain_asic_core.sv`, testbench, BOM, assembly plan, and software-only API. Inspect the actual repository paths before editing implementation.
- Mining Economics and Bitcoin Mining Intelligence are analysis/dry-run capabilities unless separate live evidence proves otherwise.
- Related open pull requests have been reported for RTL-to-GDSII, ASIC physical evidence, Bitcoin revenue reconciliation, and zero-cost RTL-to-GDSII. Review and reconcile these before duplicating implementation or merging anything.
- Keep legacy requirements and TODO records. Do not replace established architecture or claim an end-to-end operational state based on CI alone.

## 3. Separate evidence gates

Each gate must emit a machine-readable JSON report plus raw logs/artifacts where applicable. Reports must include UTC timestamp, commit SHA, tool name/version, exact command, exit code, artifact paths, SHA-256 hashes, status, and explicit limitations. Missing tools or missing evidence are `BLOCKED`/`NOT_ASSESSED`, never PASS.

| Gate | Required proof | Pass condition | Does not prove |
|---|---|---|---|
| G0 — Repository baseline | Commit, paths, open PR overlap, current workflow status | Baseline report identifies actual source and unresolved work | Runtime or hardware operation |
| G1 — Reference correctness | Known SHA-256 vectors and Bitcoin-style double-SHA-256/header serialization tests | Independent test vectors pass | Mining a valid block |
| G2 — Proof-of-work model | Target comparison, nonce search, deterministic fixtures, difficulty/target boundary tests | Valid/invalid candidate classification matches reference | Competitive hashrate or pool acceptance |
| G3 — RTL simulation | Installed simulator and version; testbench execution; retained logs | RTL agrees with reference vectors and edge cases | Synthesis or physical hardware |
| G4 — Synthesis | Yosys (or documented equivalent), logs, netlist, warnings | Synthesis succeeds and netlist is non-empty and hashed | Timing closure or silicon |
| G5 — Formal/equivalence | Available formal checks or differential test report; assumptions documented | Required properties/equivalence checks pass | Universal correctness |
| G6 — PPA estimate | Tool reports for area/timing/power with constraints and tool versions | Reproducible estimates with units and constraints | Measured silicon power/performance |
| G7 — Physical design / GDSII | Open-PDK flow, DRC/LVS reports, final GDSII, hashes, flow logs | GDSII exists and required flow checks pass | Foundry acceptance, tape-out, fabrication |
| G8 — Fabrication and silicon | Foundry/tape-out records, chip identifiers, chain of custody, physical test logs | Independent evidence of manufactured device and successful test | Pool earnings |
| G9 — Device mining | Identified real miner, measured hashrate/energy/uptime, device logs | Reproducible measurements from actual hardware | Pool acceptance or payout |
| G10 — Pool acceptance | Pool endpoint/account configured by owner, accepted/rejected share counters and pool-side evidence | Accepted shares are independently visible in the pool | Confirmed payout or profit |
| G11 — Realized revenue | Pool payout record matched to transaction on the relevant network/explorer and owner-controlled wallet receipt | Amount, asset, time, transaction ID, fees, and reconciliation are recorded | Future profitability |
| G12 — Economics | Dated electricity tariff, actual wattage, pool fees, uptime, payout and conversion fees | Transparent break-even/net result with assumptions | Guaranteed future returns |

G8 requires external fabrication evidence. G9–G11 are independent from the chip-design path: mining can be validated using an existing miner without waiting for a custom ASIC, and a fabricated chip does not itself prove mining or revenue.

## 4. Implementation sequence

### Phase A — Baseline and reference oracle
1. Inspect `brain_v12/asic/`, mining modules, current tests, workflows, and open PRs.
2. Create a small deterministic SHA-256/double-SHA-256 reference oracle and Bitcoin header/target test fixtures only where missing.
3. Validate byte order, 80-byte header serialization, target comparison, nonce boundaries, and known vectors.
4. Add a machine-readable gate report schema with fail-closed status handling.

**Exit:** G0–G2 pass in CI with retained logs and reproducible fixtures.

### Phase B — RTL verification and synthesis
1. Confirm simulator availability; prefer free/open-source Icarus Verilog or Verilator.
2. Run the RTL testbench against shared reference vectors; fix mismatches before optimizing.
3. Run Yosys synthesis where available and retain netlist, warnings, statistics, and tool versions.
4. Add formal/equivalence checks when a suitable free tool and a tractable property set are available.
5. Do not silently skip absent tools: report blocked status and reason.

**Exit:** G3–G5 pass; G6 is reported with explicit estimate-only semantics.

### Phase C — Physical-design artifact
1. Identify a compatible open PDK and supported RTL-to-GDSII flow.
2. Record constraints, versions, logs, DRC/LVS results, and all artifact hashes.
3. Require non-empty GDSII and successful required checks before marking G7 pass.
4. Treat foundry sign-off, tape-out, fabrication, and silicon test as separate external gates.

**Exit:** G7 only; no implication of fabricated silicon.

### Phase D — Existing miner / pool validation (optional, separately authorized)
1. Start with a no-cost feasibility report; do not rent hashpower, buy hardware, expose credentials, or start paid services automatically.
2. If the owner later supplies an existing miner and explicitly authorizes a live test, use a supported pool endpoint and least-privilege configuration.
3. Capture device-side hashrate and energy measurements plus pool-side accepted/rejected shares.
4. Keep secrets out of logs, commits, issue comments, and artifacts.

**Exit:** G9 and G10 only after independent device/pool evidence.

### Phase E — Payout and economics
1. Reconcile a real pool payout with the public transaction record and receipt in the owner-controlled wallet.
2. Record gross payout, pool fees, electricity cost, uptime, and conversion/withdrawal costs.
3. Report zero realized revenue until a matching payout is verified. Simulated rewards, estimated profitability, CI success, and generated reports are not revenue.

**Exit:** G11–G12 based on dated evidence, not projections.

## 5. CI and evidence contract

- Use the existing Brain verification/evidence patterns and add a dedicated ASIC lab workflow only after inspecting current workflows and open PRs for overlap.
- Run deterministic software tests on pull requests; conditionally run RTL/synthesis jobs only when tools are available, while emitting explicit blocked/not-assessed evidence when they are not.
- Store reports as workflow artifacts. Hash every important artifact with SHA-256 and include the source commit.
- A gate must fail closed on absent, empty, malformed, stale, or inconsistent evidence.
- Test both positive and negative cases: absent artifact, empty log, wrong hash, failed tool exit, invalid target, and mismatched RTL output.
- Do not automatically merge PRs to `main`. Require review and passing checks.

## 6. Resource and security constraints

- Initial budget: **0 JOD**. Free/open-source tools and CI minutes only; observe provider quotas.
- No paid cloud mining, paid compute, equipment purchases, foundry orders, or financial transactions without explicit owner approval.
- Do not request or commit wallet seed phrases/private keys. Use owner-managed secrets and least privilege for any later pool integration.
- Do not assume a personal device, Termux session, Windows host, self-hosted runner, or external service is online. Verify each execution environment independently.
- A software-only simulation is not a physical worker or ASIC.

## 7. Current status at plan creation

This file is an execution plan, not a test result. No gate is marked passed by this document. In particular, this document alone does not prove a successful RTL simulation, synthesis, GDSII generation, foundry approval, fabricated silicon, real pool shares, or realized revenue.

## 8. Definition of completion

The lab is considered complete only as a collection of independently reported gate outcomes—not one global green status. Each claim must point to its own evidence bundle. The final summary must list PASS, FAIL, BLOCKED, and NOT_ASSESSED gates separately and must never infer later-stage success from an earlier gate.

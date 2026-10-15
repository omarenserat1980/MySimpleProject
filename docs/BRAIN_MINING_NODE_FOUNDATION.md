# Brain Mining Node — Foundation and Evidence Contract

## Objective

Create a reproducible, zero-budget-first software node derived from Electronic Brain that can validate Bitcoin-mining software and ASIC designs, then connect to real mining hardware only when a real execution path is available. The node is a software-defined *control and verification node*; software alone cannot manufacture silicon, create free physical compute, or guarantee profitable Bitcoin mining.

## Operating modes (strictly separated)

- `SIMULATOR`: deterministic local simulation; all results are synthetic and labeled `SIMULATED`.
- `REFERENCE_CPU`: bounded CPU SHA-256d reference workload for correctness and benchmarking; never presented as competitive ASIC mining.
- `RTL_VERIFICATION`: HDL simulation/synthesis evidence produced by named tools and captured logs. RTL passing is not a fabricated ASIC.
- `PHYSICAL_DEVICE`: real miner telemetry collected from an identified device, with timestamped provenance.
- `POOL_CONNECTED`: authenticated Stratum connection and submitted shares; accepted shares must be evidenced by pool responses.
- `PAYOUT_VERIFIED`: independently reconciled payout evidence; never inferred from hashrate, shares alone, a simulator, or CI.

A mode may not silently promote itself to another. Missing or contradictory evidence fails closed.

## Node components

1. **Clone/identity manager** — create a separate node configuration and identity; never copy private credentials or reuse another node's identity.
2. **Brain supervisor adapter** — register capability, health, last heartbeat, and bounded task status.
3. **ASIC model adapter** — reuse the existing `/api/asic-sim` interface and label its outputs simulated.
4. **SHA-256d reference worker** — bounded correctness workload with deterministic vectors and an independent reference implementation; no pool connection by default.
5. **RTL evidence adapter** — record tool name/version, source commit, command, exit status, log digest, and artifact digest for each RTL/synthesis run.
6. **Mining protocol adapter** — disabled by default; if implemented, require explicit configuration, authenticated transport where supported, bounded resource usage, and clear reporting of accepted/rejected shares.
7. **Evidence registry** — append-only event records with schema version, node ID, mode, UTC timestamp, source commit, evidence type, digest, and verification result.
8. **Safety/economics gate** — no paid service, purchase, wallet transfer, or financial side effect without explicit authorization. Report cost and revenue as unknown until independently measured.

## Readiness gates

- **G0 — Importable:** modules import; schemas validate; no secret values committed.
- **G1 — Simulation:** deterministic tests pass; simulated data cannot be classified as real.
- **G2 — Algorithm correctness:** known SHA-256/SHA-256d test vectors pass against an independent reference; nonce search is bounded.
- **G3 — RTL evidence:** actual RTL simulator/synthesis tool is installed; tool versions and logs are captured; missing tools yield BLOCKED, not PASS.
- **G4 — Device evidence:** a real device is identified and its telemetry source is authenticated and timestamped.
- **G5 — Pool evidence:** real connection and pool acknowledgements/shares are recorded; test fixtures cannot satisfy this gate.
- **G6 — Payout evidence:** payout transaction and destination are reconciled with an independent chain source and minimum confirmations.
- **G7 — Profit evidence:** measured attributable electricity/hosting/fees and verified payout are reconciled over the same period.

Only G0-G3 can be completed entirely in software without a real device or external service. G4-G7 require corresponding real-world evidence. A successful workflow alone never proves mining or revenue.

## Resource and cost constraints

- Default to local/offline operation and free CI runners only within their published limits.
- Do not assume GitHub Actions is a continuous 24/7 mining host; hosted runners are ephemeral and subject to quotas and acceptable-use rules.
- Do not claim virtual CPU/RAM/ASIC capacity as physical compute or as a source of real hash rate.
- Never store tokens, wallet private keys, passwords, or pool credentials in Git.
- No external mining pool, wallet, paid cloud, or deployment is contacted by simulation or test mode.

## Required status contract

Every result should include:
```json
{
  "node_mode": "SIMULATOR",
  "state": "SIMULATED",
  "source_commit": "<commit-sha>",
  "started_at": "<UTC timestamp>",
  "completed_at": "<UTC timestamp>",
  "evidence": [],
  "blockers": [],
  "real_mining_claim": false,
  "revenue_claim": false
}
```

Real-mode records must identify their evidence sources and may not use synthetic fixtures. Never include secrets in evidence output.

## Immediate implementation sequence

1. Add contract schemas and unit tests for mode separation and fail-closed evidence classification.
2. Wire the existing ASIC simulator and mining-intelligence dry-run APIs through a single node-status response.
3. Add bounded SHA-256d correctness tests and label their results as reference computation.
4. Capture RTL tool availability, versions, source revision, exit code, and artifact hashes in CI.
5. Add device, pool, payout, and profit adapters only behind the corresponding evidence gates.
6. Verify the branch with CI and review before merging; do not activate real mining automatically.

## Explicit non-goals

This foundation does not claim a fabricated ASIC, physical hardware, cloud capacity, real pool shares, a wallet payout, revenue, or profit. It does not bypass proof-of-work difficulty or make ordinary software competitive with dedicated Bitcoin ASICs. The goal is to remove software integration and verification blockers while accurately surfacing blockers that require real hardware, tools, connectivity, or funds.

# Bitcoin SHA-256 / Proof-of-Work RTL prototype

## Implemented digital blocks

- `sha256_compress.sv`: combinational SHA-256 compression for one 512-bit block.
- `sha256d_header_hash.sv`: SHA-256d hash calculation for an 80-byte Bitcoin header, including little-endian nonce serialization.
- `bitcoin_pow_target_check.sv`: byte-order-aware comparison of the raw digest against a conventional big-endian target.
- `bitcoin_nonce_sweep.sv`: bounded sequential nonce search with a configurable per-run attempt budget and a hard maximum.

## Hosted verification evidence

The `Bitcoin SHA-256 compression RTL` GitHub Actions workflow installs Icarus Verilog on an ephemeral GitHub-hosted runner, compiles the RTL, runs the testbenches, and uploads simulation logs as an artifact.

Latest recorded successful integrated run for the genesis-nonce search:
- Run: [38568698782](https://github.com/omarenserat1980/MySimpleProject/actions/runs/38568698782)
- Checked-out source: merge commit `82661f4` (GitHub Actions log: `HEAD is now at 82661f4 Merge 4d4c74d687abe00edd3ca55d456318e6cf6f314c into 2ad98ff9a060d738215c5334f99502148121ea8f`).
- Tested change: `4d4c74d687abe00edd3ca55d456318e6cf6f314c`, merged into base `2ad98ff9a060d738215c5334f99502148121ea8f` for PR validation.
- Note: the log line `Commit: c3d12f3313a95f25162a1503be624f3b0617f8c0` appears in the runner-image metadata before checkout; it is not the repository checkout SHA. The checkout command and subsequent `HEAD is now at` line identify the tested source.
- Job conclusion: `success`
- The suite includes the SHA-256 empty-message known-answer test, Bitcoin Genesis SHA-256d header vector, target comparator checks, bounded nonce-sweep exhaustion/easy-target tests, and a Genesis nonce search starting one nonce before the known nonce with a two-attempt budget.

## Scope limits and next gates

These results prove digital RTL simulation against the included vectors and bounded search tests only. They do **not** prove an FPGA/ASIC is running, a physical ASIC has been fabricated, a live Bitcoin pool connection exists, shares were accepted, or any Bitcoin/revenue was received.

The nonce sweep is a correctness prototype, not a throughput-optimized miner: it evaluates a combinational SHA-256d path and tests a bounded candidate range. Real mining evidence would require independently verifiable hardware/runtime identity, sustained measured hash rate, live pool session and accepted-share records. Revenue requires separate payout/ledger evidence. Physical ASIC fabrication and silicon validation are separate gates.

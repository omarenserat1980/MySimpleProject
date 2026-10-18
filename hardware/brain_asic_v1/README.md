# Brain ASIC v1 — Cloud Build

Purpose: use cloud CI as the repeatable RTL development environment.

## Current contents
- `rtl/brain_sha256_compress.sv`: combinational SHA-256 compression round function, accepting an initial 256-bit state and one 512-bit padded message block.
- `tb/brain_sha256_compress_tb.sv`: known-answer test for the SHA-256 empty-message padded block.
- `reference/bitcoin_sha256d.py`: independent software SHA256d/header proof-of-work reference.
- `reference/test_bitcoin_sha256d.py`: genesis-block header hash and input validation tests.
- `rtl/brain_sha256_core.sv`: control shell only; its current comparison is a placeholder and is NOT a Bitcoin miner.

## Pipeline
1. Python reference tests
2. Icarus Verilog known-vector and control-path tests
3. Yosys synthesis and JSON netlist artifact
4. Later: integrate two SHA-256 passes, the 80-byte header/nonce datapath, target comparison, and verified vectors
5. Only after RTL gates pass: physical design with a compatible PDK, timing/area checks, signoff, and foundry process

## Acceptance gates
- CI tests pass and evidence artifacts are retained.
- Compression known-answer test passes.
- Full Bitcoin header SHA256d RTL matches the independent reference across known vectors.
- No revenue is recorded from simulation or synthesis.
- No "physical ASIC" status until fabrication and hardware bring-up evidence exists.

**Status warning:** the SHA-256 compression block is not yet integrated into the control shell, and the full double-SHA256 mining datapath is not implemented. A synthesized netlist is not physical silicon and does not mine Bitcoin by itself.

# Bounded Bitcoin Proof-of-Work Simulation

This module adds a small, deterministic software lab for the SHA-256d proof-of-work primitive.

## What it does

- Accepts an 80-byte candidate block header and a 256-bit target.
- Replaces the four-byte nonce at header offset 76 using Bitcoin's little-endian nonce encoding.
- Computes SHA256(SHA256(header)) and compares the hash as a little-endian integer with the supplied target.
- Stops after a caller-specified bound; the implementation rejects bounds above 1,000,000 attempts.
- Emits explicit evidence scope: `BOUNDED_OFFLINE_SOFTWARE_SIMULATION`.

## What a passing test proves

It proves that the Python function follows the tested byte/nonce/target contract for deterministic test inputs. It is useful for software validation and as a reference for a future RTL implementation.

## What it does not prove

It does **not** prove Bitcoin network participation, production mining, pool authentication, accepted shares, real hashrate, ASIC RTL equivalence, fabricated silicon, a wallet payout, or revenue. It has no network, pool, or wallet code and does not run a continuous miner. The easy-target test is deliberately trivial and is not a mining-performance benchmark.

## Next independent proof gates

1. Compare the implementation against independently sourced Bitcoin header/hash test vectors.
2. Build and simulate a dedicated SHA-256d RTL datapath, then prove equivalence against this reference on the same vectors.
3. Synthesize the RTL and retain tool versions, constraints, logs, and output hashes.
4. Treat tape-out/fabrication and physical silicon measurements as separate gates.
5. Treat a real pool session, accepted shares, and a confirmed payout as separate external evidence gates.

All steps here are software-only and intended for free GitHub-hosted CI. No merge to `main`, paid service, device, pool, or wallet is required by this change.

# Electronic Brain — Proof Gate Architecture

## Current implementation

The current `main` branch contains:
- `brain_v12/brain/proof_gate_engine.py`: validates evidence envelopes and freshness/revision constraints.
- `brain_v12/brain/proof_registry.py`: declares separate runtime, live-mining, revenue, GDSII, foundry, silicon, and device-execution proof contracts.
- Focused tests in `brain_v12/tests/test_proof_gate_engine.py` and `brain_v12/tests/test_proof_registry.py`.
- `.github/workflows/proof-gate-engine-tests.yml`: focused test workflow.

This evaluator validates structure and consistency. It does not independently authenticate a claimed source, contact a live pool, prove a payment, or prove physical manufacture. A valid hash establishes integrity relative to that hash, not truth or provenance.

## Decision states

- `PASS`: all required proof types have acceptable, fresh evidence matching configured constraints.
- `FAIL`: supplied evidence fails a required validation.
- `BLOCKED`: required evidence is absent.
- `UNKNOWN`: gate configuration or evaluation parameters are invalid.

Do not convert an envelope-validation result into a broader real-world claim.

## Evidence policy

Each record should carry, where applicable:
- evidence ID and proof type;
- source type/reference and verification method;
- observed/collected timestamps, run ID, commit SHA, environment;
- status, measurement and unit;
- artifact reference and SHA-256;
- limitations and audit event reference.

Never place secrets, private keys, access tokens, or raw wallet credentials in evidence records. Reject synthetic/test/fixture evidence for real-world gates. Enforce freshness, identity, and commit association where the gate requires them.

## Separate proof domains

### Software and runtime
Bind test and health reports to the exact commit/run. Green CI is evidence of the tested software path, not every deployment or physical device.

### Live mining
Require authenticated pool-origin evidence for worker identity, positive observed hashrate, and accepted shares. Local counters and simulated jobs are not pool proof. Pool activity does not prove payout.

### Realized revenue
Require independent reconciliation of provider payout and blockchain confirmation, including network, asset, amount, fees, and duplicate prevention. Forecasts, balances, and pending transactions are not realized revenue. Verification must not initiate withdrawals or move funds.

### ASIC and silicon
Keep RTL simulation, synthesis, formal verification, physical design, DRC/LVS, timing signoff, GDSII artifact validation, foundry acceptance, manufacture, and silicon test as separate gates. CI synthesis does not prove fabricated silicon or a deployed miner.

### Device execution
Require authenticated device identity, fresh heartbeat, task ID, execution result, and postcondition. A queued command or reachable API alone is not execution proof.

## Self-healing acceptance

Use bounded, auditable stages such as:

`SCAN → REVIEW → DIAGNOSE → PLAN → PATCH → TEST → VERIFY → PROOF GATE → ACCEPT/REJECT → AUDIT`

The repair mechanism must not be the sole approver of its own changes. Preserve rollback material, bound retries, and record rejection reasons. Keep cost, permission, and external-side-effect gates independent.

## Acceptance criteria

- Missing, stale, synthetic, conflicting, or mismatched evidence cannot unlock a real-world gate.
- Decisions include reasons and traceable evidence identifiers.
- Physical and financial claims remain blocked until their own independent evidence is present.
- Existing domain-specific gates remain authoritative; this shared evaluator complements rather than replaces them.

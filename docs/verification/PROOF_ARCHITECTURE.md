# Universal Proof & Evolution Factory — Architecture

## Status and baseline

- Repository: `omarenserat1980/MySimpleProject`
- Baseline branch: `main`
- Baseline commit inspected: `a14e0db199c1cb3d991db30b16eea43a2150f41e`
- Working branch: `brain/universal-proof-evolution-v1`
- This document records architecture and proof boundaries; it does not claim that new runtime components have already been implemented or tested.

## Design principles

1. Evidence is separate from execution and separate from a caller's success flag.
2. Proof gates are fail-closed: missing, stale, synthetic, conflicting, or unverifiable evidence cannot produce `PASS`.
3. Every proof result records its scope and limitations. A software test cannot prove a physical or financial outcome.
4. Use existing modules and storage before introducing new frameworks, databases, API routes, or workflows.
5. No paid resources, automatic withdrawals, automatic purchases, or automatic merge to `main`.
6. Simulated and test evidence must be explicitly labelled and must never enter realized-revenue accounting.
7. Keep evidence provenance, timestamps, run identifiers, and commit association wherever available.

## Existing primitives discovered — reuse before extending

The baseline already contains `brain_v12/brain/verification_gate.py`, a `VerificationGate` that distinguishes action completion from objective verification and hashes evidence references. It also contains `brain_v12/digital_lab/UNIVERSAL_ENGINEERING_GATE_CONTRACT.md`, which defines lifecycle states, evidence minimums, domain checks, and fail-closed acceptance. The master specification already separates engineering health from commercial outcomes.

Therefore, do not create a parallel verification gate or replace these contracts. The implementation should first map their current semantics and tests, then add only missing shared evidence provenance, freshness, source validation, audit persistence, and domain adapters. Preserve existing response contracts unless a reviewed migration proves a compatible change is required.

## Proposed logical components

- **Proof Registry:** declarative definitions of gates, required evidence, freshness windows, and acceptance policies.
- **Evidence Collector:** adapters for existing test reports, runtime health checks, device heartbeats, mining-pool telemetry, blockchain data, and ASIC artifacts.
- **Evidence Validator:** schema, provenance, timestamp/freshness, artifact digest, identity, consistency, and environment checks.
- **Gate Evaluator:** deterministic `PASS`, `FAIL`, `BLOCKED`, `UNKNOWN`, or `NOT_APPLICABLE` decisions.
- **Evidence Ledger:** append-oriented audit records with references and digests; do not claim tamper-proof storage unless an independently enforced mechanism proves that property.
- **Policy Layer:** least privilege, operation risk, cost limits, human authorization, and explicit separation of read-only verification from side effects.
- **Verification API/UI:** expose current gate state and evidence references by reusing existing API/UI conventions.

## Common evidence contract

Recommended fields, where applicable:

- `evidence_id`, `proof_type`, `subject_id`
- `source_type`, `source_reference`, `verification_method`
- `observed_at`, `collected_at`, `run_id`, `commit_sha`, `environment`
- `status`, `measurement`, `unit`
- `artifact_reference`, `artifact_sha256`
- `freshness_policy`, `verifier_version`, `limitations`, `audit_event_id`

A digest establishes content integrity relative to the digest; it does not by itself prove that the content is truthful or came from the claimed source. Do not store secrets, private keys, access tokens, or raw wallet credentials in evidence records.

## Gate families

### Runtime and software changes
- Runtime readiness and component-specific health checks.
- Unit, integration, regression, security, and recovery tests.
- Bind test reports to the commit and run that produced them.
- A successful API endpoint or green CI run is not proof that all components or physical devices are operational.

### Bitcoin mining
- Require evidence from a real miner and a real pool connection.
- Verify observed hashrate and accepted/rejected shares against pool-origin evidence, with timestamps and worker identity safely redacted.
- Keep simulated values and local counters labelled as test-only.
- Mining evidence does not prove payout or revenue.

### Revenue
- Independently reconcile provider payout records with the matching blockchain transaction, network, asset, amount, fee, destination fingerprint, and confirmation policy.
- Prevent duplicate transaction recognition.
- Keep forecast, provider balance, requested payout, pending transaction, confirmed payment, realized revenue, and verified profit as separate states.
- Never initiate withdrawals or move funds as part of verification.

### ASIC and GDSII
Use separate gates for RTL source, simulation, synthesis/netlist, formal verification, physical design, DRC, LVS, timing signoff, GDSII artifact validation, foundry acceptance, silicon manufacture, and silicon test. Require actual files and tool reports for digital stages; require independent external evidence for foundry acceptance, manufacture, and silicon test. A GDSII file is not proof of manufactured silicon.

### Device execution
- Verify authenticated device identity, client version, heartbeat freshness, task ID, exit status, logs, and postcondition.
- Sending a command is not proof that it ran; API availability is not proof that a phone or Windows host is connected.

### Commercial delivery
- Separate offer/opportunity, customer validation, order, delivery, payment verification, realized revenue, and verified profit.
- Recognize realized revenue only from auditable evidence and avoid duplicate records.

## Self-healing integration

Use the existing lifecycle where possible:

`SCAN → REVIEW → DIAGNOSE → PLAN → PATCH → TEST → VERIFY → PROOF GATE → ACCEPT/REJECT → AUDIT`

The repair mechanism must not be the sole approver of its own changes or change the policy and approve that policy change in the same trust domain. Bound retries, preserve rollback material, and record why a change was accepted or rejected.

## Implementation sequence

1. Inventory existing proof, mining, revenue, ASIC, runtime, and self-healing components.
2. Map existing evidence schemas and APIs; identify overlap before creating new abstractions.
3. Define gate contracts and evidence provenance.
4. Implement a minimal shared evaluator and tests.
5. Integrate mining/revenue and ASIC gates through adapters, preserving current behavior.
6. Add device and self-healing integrations.
7. Add dashboard/API views only after stable underlying contracts exist.
8. Test persistence, replay, duplicates, tampering, stale data, missing evidence, and recovery.
9. Publish a proof-gap report and retain all physical/financial claims as blocked until independent evidence exists.

## Acceptance criteria

- No missing or synthetic evidence can unlock a real-world gate.
- All decisions have a reason and traceable evidence references.
- Tests explicitly cover missing, stale, mismatched, duplicated, conflicting, and synthetic evidence.
- Existing endpoints and modules are reused where practical.
- Security and cost constraints remain enforced.
- The change is not merged into `main` automatically.

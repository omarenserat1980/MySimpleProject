# Brain Tool Lifecycle: Simulation → Real Implementation

## Mandatory rule

Every newly developed Brain tool starts with a deterministic simulation for fast,
safe contract testing. Once simulation passes, Brain immediately attempts to build
the real adapter. Simulation is a development stage, never proof of real-world
operation and never a substitute for the real adapter.

## Required progression

`CREATED → SIMULATING → SIMULATION_PASSED → BUILDING_REAL → REAL_BUILT → VERIFYING_REAL → REAL_VERIFIED`

Optional final activation is `REAL_VERIFIED → ACTIVE`, and requires explicit
authorization. Missing dependencies, credentials, network access, hardware, or
permissions must produce a clear blocked/failed result—not synthetic success.

## Evidence contract

- The simulation result must be literal `True`.
- The real builder must return a concrete implementation, not `None`.
- The real verifier must return a non-empty evidence mapping with `verified: true`.
- Evidence should identify the real operation, timestamp/run, target/provider,
  outcome, and relevant logs or artifact references where available.
- A test double, mock, simulator result, workflow queue state, or green CI status
  alone is not real-world evidence.
- If verification fails, preserve diagnostics and keep the tool non-active.
- Never claim a device, cloud VM, external account, payment, or service exists
  unless independently checked.

## Implementation

`brain_v12/tool_lifecycle.py` provides a small fail-closed orchestration primitive.
Each concrete tool must supply its own simulation, real adapter builder, and
independent verifier. This primitive does not create credentials or grant access
to external systems. Activation is permission-gated and optional.

## Safety and change control

- Keep secrets out of source control; use approved environment/secret stores.
- Use least-privilege credentials and bounded retries.
- External side effects (publishing, purchases, payments, withdrawals, legal
  submissions, destructive operations) require their own explicit authorization.
- Make changes on a feature branch, run focused tests and CI, inspect evidence,
  then merge through the repository's normal review gate. Never auto-edit `main`
  as part of self-healing.
- Record truthful states: `SIMULATED`, `REAL_IMPLEMENTATION_READY`,
  `REAL_VERIFIED`, `ACTIVE`, or `BLOCKED`; do not conflate them.

## Initial verification scope

The unit tests verify orchestration order and fail-closed behavior. They do not
prove any external adapter, device, cloud runtime, or production integration is
already available. Each adapter needs its own integration test and evidence.

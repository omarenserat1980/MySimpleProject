# Electronic Brain — Revolutionary Engineering Upgrade

## Purpose

Turn the existing Brain codebase into an evidence-driven engineering control plane. This document is an implementation plan, not a claim that the listed capabilities are already operational.

## Repository facts observed during the initial read-only review

- The default branch is `main`.
- `brain_v12/app.py` currently labels the application as Electronic Brain V14 and imports existing `EvidenceStore`, `VerificationEngine`, `BrainSelfMonitor`, workload-routing components, and device/cloud-federation components. Confirm version/deployment alignment before treating a version label as proof of the live deployment.
- The application has background-work handlers named `simulation_health`, `simulation_inventory`, and `simulation_readiness`; their event records explicitly mark reality as `SIMULATED`.
- The remote-fabric routes are documented in code as simulation-first. A successful virtual-twin command must never be reported as proof of a real Arkan/Windows host connection.
- The Windows cloud launch workflow defaults both `approve_apply` and `cost_reviewed` to false. Provisioning Azure resources is a separate, cost-bearing action and is not part of this roadmap change.
- The expected device-link file path `brain_v12/tools/brain_device_link.py` was not found at that path during this review. Search the current tree for the canonical implementation before editing it; do not infer the path from an older note.

## Engineering principles

1. Evidence before diagnosis; diagnosis before mutation.
2. Read-only discovery is the default.
3. Prefer existing components and canonical owners over parallel implementations.
4. Keep simulation, mock, configured, reachable, authenticated, and end-to-end verified states distinct.
5. Never print credentials, tokens, private keys, or sensitive environment values.
6. No cloud resource creation, paid service changes, secret rotation, access expansion, deletion, or production deployment without explicit scoped approval.
7. Every mutation must be bounded, logged, testable, and reversible where practical.
8. A created file, successful HTTP response, queued job, or passing unit test alone does not prove end-to-end operation.

## Delivery phases

### Phase 0 — Baseline and inventory

- Capture default branch/commit, repository structure, current tests, workflow definitions, and deployment configuration.
- Inventory canonical health, evidence, verification, device-authentication, and remote-execution modules.
- Map each important claim to a repeatable test or runtime observation.
- Produce a baseline report without changing production or cloud resources.

**Acceptance:** report includes paths, commit references, commands/tests run, observed results, and unknowns. No unsupported claims.

### Phase 1 — Unified evidence and health contract

Define a consistent read-only status contract with fields such as:

- `component`, `observed_at_utc`, `status`, `reality`, `source`
- `last_success_at`, `last_error_code`, `evidence_ids`
- `configured`, `reachable`, `authenticated`, `end_to_end_verified`

Unknown values must remain unknown rather than being coerced to true. Do not expose secrets or raw authorization headers.

**Acceptance:** unit tests cover missing configuration, stale observations, unreachable targets, authentication failures, and simulated-vs-real labeling.

### Phase 2 — Root-cause diagnosis and safe repair

- Normalize exceptions and service errors into stable error codes.
- Correlate errors with logs, health observations, workflow results, and recent changes.
- Generate a minimal repair plan with confidence and supporting evidence.
- Require an allowlisted action, scope check, timeout, idempotency key, and audit event for every automated mutation.
- Run checks in an isolated environment where available; verify after applying a change.
- Stop and report when evidence or rollback capability is insufficient.

**Acceptance:** injected-failure tests prove that the system diagnoses correctly, avoids unsafe actions, and never reports a repair as successful before verification.

### Phase 3 — Device identity and real connectivity

- Discover the current canonical device-agent and authentication modules before changing code.
- Give each device a stable identity and independently scoped credentials.
- Distinguish missing credentials, invalid credentials, stale heartbeat, transport failure, and successful authenticated response.
- Test a harmless round trip: Brain sends a nonce/task ID; the authorized device returns the same identifier plus a result; Brain validates freshness and identity.
- Do not weaken authentication or modify Android permissions/UIDs as a shortcut.

**Acceptance:** tests cover unauthorized devices, replayed/stale responses, wrong device IDs, timeouts, and a successful authenticated round trip. Real-device success requires fresh runtime evidence.

### Phase 4 — Regression lab and recovery

- Reuse the existing test framework and canonical CI workflows.
- Add focused tests around each repaired behavior and relevant regressions.
- Preserve the pre-change commit and use a dedicated branch/pull request.
- Use rollback only when the current change is attributable and rollback is safe.

**Acceptance:** test commands and outcomes are recorded; failures remain visible; no CI pass is fabricated or inferred.

### Phase 5 — Unified operations and resource economics

- Build a read-only inventory across GitHub, Render, Azure, and device agents using available authorized connectors.
- Label each data source with observation time and confidence.
- Show projected cloud costs and require explicit approval before creating paid resources.
- Treat a Terraform template or workflow as desired state, not proof that a VM exists.
- Require cloud provisioning state, power state, guest OS checks, network-policy checks, and a client-side RDP test before declaring Windows Server ready.

**Acceptance:** resource states are grounded in live provider evidence; unavailable connectors are reported as blockers, not replaced with guesses.

### Phase 6 — Engineering memory and learning

- Store incident summaries, evidence references, diagnosis, change, tests, and verified outcome.
- Reuse previous incidents only when the underlying evidence is relevant.
- Do not mark an incident resolved if verification is absent.
- Track recurring failures and recommend preventive tests.

**Acceptance:** repeated-incident tests demonstrate retrieval and correct unresolved/resolved status.

## Required final report for every execution

Report:
1. Scope and authorization used.
2. Exact paths, services, and commits inspected.
3. Commands and tests actually run, with results.
4. Changes made and their commit/branch/PR.
5. Runtime evidence and its timestamp.
6. Simulation vs real-system status.
7. Remaining blockers and uncertainty.
8. Cost/security implications and rollback instructions.

## Initial execution boundary

This roadmap change is documentation-only. It does not modify application code, secrets, GitHub Actions settings, Render configuration, Azure resources, or physical devices. Implement phases incrementally in separate reviewed changes, beginning with Phase 0 and Phase 1.
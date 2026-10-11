# Electronic Brain Resource Factory — Phase 1

## Discovery decision

The repository already contains ASICResourceAdapter, TaskEngine, CapabilityRegistry,
WorkerRegistry, HealthProbeEngine, and EvidenceStore. This milestone composes those
components instead of adding a second ASIC adapter, executor registry, or evidence database.
The repository also has resource_manager.py for virtual blade capacity, cloud_hardware.py
for typed hardware manifests, and economic_ledger.py for evidence-based revenue records.

## Changes in this milestone

- brain_v12/brain/resource_factory.py: bounded N-node ASIC simulator factory; shared adapter
  registry; resource-registration evidence; explicit simulated truth level; reservation,
  execution-state transition, quarantine, and evidence-checked recovery.
- brain_v12/brain/profit_gate.py: fail-closed expected-economics gate; blocks simulation,
  unverified providers, insufficient evidence, unverified truth levels, missing revenue/costs,
  and non-positive expected net; exposes a kill-switch decision without moving money.
- brain_v12/tests/test_resource_factory.py: focused regression coverage for scale, duplicate
  prevention, deterministic simulated workload output, lifecycle/reservation, quarantine/recovery,
  and economic blocking/approval.
- Existing brain-cloud-mining-control workflow is extended to run these focused tests; no new
  workflow is created.

## Truth and safety boundary

All nodes created here have execution_mode=SIMULATOR, truth_level=SIMULATED,
real_device=false, real_mining=false, and revenue_verified=false. Evidence hashes establish
payload integrity only; they do not attest physical identity or external truth. The profit gate
returns an expected-economics decision only and does not write REALIZED_REVENUE, access a wallet,
connect to a pool, provision paid capacity, or send payments.

## Explicitly not complete

This is an incremental milestone, not the full master specification. Generic CPU/RAM/GPU/storage/
remote-compute scheduling, real device attestation, externally verified execution, external payout
verification, a full 50-case matrix, live-device evidence, and real revenue remain NOT VERIFIED.
The local working tree on the user's devices cannot be inferred from GitHub API state. No automatic
merge is authorized.

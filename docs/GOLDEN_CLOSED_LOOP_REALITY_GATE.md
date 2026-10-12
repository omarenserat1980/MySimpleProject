# Golden Closed Loop — Evidence Gate

## Scope
Target: 100 physical ASIC devices and one Windows Server host managed by Electronic Brain. This is an acceptance contract, not proof that hardware is connected or mining has started.

## Verified source boundary
- `brain_v12/brain/asic_resource_adapter.py` supports SIMULATOR, REMOTE_PROVIDER, and PHYSICAL_DEVICE records, but its module documentation says it does not connect to providers or start mining.
- Simulator fleets may contain up to 128 records, but simulator records are not physical devices.
- External telemetry is caller-supplied and untrusted. Hash verification protects payload integrity; it does not prove device identity.
- `release_gate` blocks activation until external identity attestation exists.
- `brain_v12/brain/mining_engine.py` calculates from supplied inputs and leaves revenue unverified.
- `brain_v12/brain/bitcoin_mining_intelligence_api.py` is analysis/dry-run only and reports real mining disabled.
- Existing tests validate software guardrails, not live ASIC operation or Windows boot.

## Mandatory order
1. Preserve simulation/physical-device separation. Do not bypass the existing release gate.
2. Obtain fresh authenticated Windows Server evidence: OS identity/version, resources, connectivity, and a successful non-destructive task.
3. Connect one authorized physical ASIC through a model-specific, read-only adapter. Require fresh telemetry and independently attested identity.
4. Verify live pool work and accepted-share evidence before declaring mining active.
5. Keep pool rewards, confirmed payouts, measured/estimated electricity costs, and operating costs as separate ledger entries.
6. Expand only after one device passes; count 100 distinct, attested physical devices, never generated simulator IDs.
7. Test recovery with non-destructive failures and preserve before/after evidence.

## Acceptance gates
- `CODE_VERIFIED`: relevant CI tests pass.
- `WINDOWS_SERVER_BOOT_VERIFIED`: authenticated host evidence and a successful guest task.
- `ASIC_CONNECTED_VERIFIED`: physical identity, fresh telemetry, and health checks.
- `BITCOIN_MINING_VERIFIED`: live pool work and accepted shares from a physical ASIC.
- `PAYOUT_VERIFIED`: independently checked on-chain receipt matching the payout.
- `ASIC_100_INVENTORY_VERIFIED`: 100 distinct, independently attested physical devices.
- `ECONOMIC_LEDGER_VERIFIED`: costs and confirmed revenue reconciled with provenance.
- `RECOVERY_VERIFIED`: a documented failure/recovery test with valid evidence.

A hash of caller-supplied JSON alone is not proof of physical identity or mining. A passing software test is not proof of a live device.

## Safety
No paid service is enabled without approval. Never request or store wallet seed phrases or private keys. Begin with read-only telemetry and one authorized ASIC. Do not apply fleet-wide configuration or firmware changes without explicit authorization and a rollback plan.

## Current status
The inspected code does not establish live connectivity to 100 ASICs, independent physical identity attestation, real pool work, or a Windows Server boot. The next step is to connect and verify one real ASIC and collect authenticated Windows Server evidence. Until then, report a blocked/partial state, not success.

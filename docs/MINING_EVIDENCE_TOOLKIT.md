# Mining Evidence Toolkit — Brain V12

## Purpose
Provide offline, evidence-first investigation tooling without claiming that a simulator, registered worker, or dashboard status is a real miner. This toolkit does not start miners, connect to pools, access wallets, provision resources, or change production settings.

## Current command
```bash
python -m brain_v12.tools.mining_evidence_audit audit evidence.json --output audit-report.json
python -m brain_v12.tools.mining_evidence_audit profit payout-ledger.json --output profit-report.json
```

## Evidence model
An evidence JSON record may contain:
- `execution_mode`: PHYSICAL_DEVICE or REMOTE_PROVIDER; SIMULATOR is always rejected as real mining.
- `device_identity`: `serial_or_provider_id` plus an independent identity attestation reference.
- `telemetry`: `observed_at` (ISO-8601 UTC) and `hashrate_hs`, from a trusted device/provider adapter.
- `pool`: `pool_id`, `worker_id`, verified session and independently verified accepted shares.
- `payout`: currency, amount, transaction ID, and independent verification reference.
- `costs`: electricity, pool_fees, hosting, and other costs.
- `evidence_refs`: source references for each critical gate.

A JSON boolean or a hash is not itself proof. An authorized investigator must verify references against independent device, pool, payment, and cost sources. The tool's status `EVIDENCE_COMPLETE_REQUIRES_HUMAN_REVIEW` is not an automatic authorization to mine.

## Profit calculation
The calculator only sums payout entries marked independently verified and rejects duplicate transaction IDs, currency mismatches, invalid amounts, and unverified payouts. It subtracts recorded electricity, pool fees, hosting, hardware amortization, and other costs. Ensure the ledger uses one consistent currency and time period. It does not fetch exchange rates or estimate unmeasured electricity.

## Next integrations (separate, explicit work)
1. Add a model-specific read-only physical ASIC adapter after the actual model, authenticated interface, and operator authorization are known.
2. Add a pool-specific read-only adapter after the pool is identified; never put credentials in source, logs, fixtures, or reports.
3. Verify payout transaction IDs through the appropriate independent chain explorer or payment provider.
4. Attach evidence artifacts and test logs in CI; CI proves code behavior, not real-world mining.
5. Keep Render checks read-only. Do not deploy or merge as part of this toolkit change.

## Test
```bash
python -m unittest brain_v12.tests.test_mining_evidence_audit -v
```

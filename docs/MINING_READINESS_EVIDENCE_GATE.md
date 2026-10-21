# Mining readiness evidence gate

`brain_v12.brain.mining_readiness_gate.evaluate_mining_readiness` classifies supplied evidence only. It performs no network calls and cannot start a miner, authorize a Stratum worker, submit shares, modify pool settings, or move funds.

The gate fails closed unless read-only device evidence, a reported local hashrate, Stratum reachability, payout-address configuration, accepted-share evidence, independently verified block-reward evidence, and payout evidence are all present. Pool-wide telemetry and a successful `mining.subscribe` response are not local mining or revenue evidence.

The current implementation intentionally keeps `readiness_for_real_mining`, `real_mining_verified`, `revenue_realized`, and `financial_execution_enabled` false. Any future promotion requires a separately reviewed evidence contract; this classifier itself never authorizes execution.

## Read-only API

The `mining_readiness_api` router exposes `GET /api/mining/readiness`. It reads the existing CKPool evidence file and performs only the configured ASIC connector's allowlisted read-only calls. The optional `BRAIN_BTC_PAYOUT_ADDRESS` variable is checked for presence only; the address is never returned by the endpoint. Missing evidence remains blocked. In this working tree the router is mounted in `brain_v12/app.py`; that file already contains unrelated local edits and is intentionally excluded from this isolated commit.

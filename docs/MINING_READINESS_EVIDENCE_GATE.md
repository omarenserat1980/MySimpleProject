# Mining readiness evidence gate

`brain_v12.brain.mining_readiness_gate.evaluate_mining_readiness` classifies supplied evidence only. It performs no network calls and cannot start a miner, authorize a Stratum worker, submit shares, modify pool settings, or move funds.

The gate fails closed unless read-only device evidence, a reported local hashrate, Stratum reachability, payout-address configuration, accepted-share evidence, independently verified block-reward evidence, and payout evidence are all present. Pool-wide telemetry and a successful `mining.subscribe` response are not local mining or revenue evidence.

The current implementation intentionally keeps `readiness_for_real_mining`, `real_mining_verified`, `revenue_realized`, and `financial_execution_enabled` false. Any future promotion requires a separately reviewed evidence contract; this classifier itself never authorizes execution.

# Brain ASIC Hosting — Zero-Budget Gate

## Goal

Let Electronic Brain evaluate a hosted physical Bitcoin ASIC offer without asking the user to buy a server or commit funds. Brain is the control/monitoring layer; the ASIC itself must be operated by a real hosting provider or later-owned physical hardware.

## Current reality

- Render's `brain-control-plane-main` is a free web service, not an ASIC and not a profitable Bitcoin miner.
- The Brain controller does not create mining capacity by itself.
- With a budget of USD 0, an offer must explicitly provide a genuine trial whose rewards are withdrawable to an external wallet, with no deposit, activation fee, recurring charge, paid upgrade, referral unlock, or withdrawal fee.
- A provider's own dashboard balance is not proof of a payout. Verify an on-chain transaction or a pool payout independently before treating any amount as revenue.

## Brain resource adapter

`brain_v12/brain/asic_resource_adapter.py` connects ASIC entries to the existing Brain capability registry, task engine, health probes, evidence store, and mining economics engine. It supports three isolated execution modes:

- `SIMULATOR`: deterministic arithmetic estimates from supplied hashrate and duration. It does not perform SHA-256 mining, contact a pool, represent a physical device, or produce revenue.
- `REMOTE_PROVIDER`: an externally hosted resource record. Registration alone does not establish provider identity or service availability.
- `PHYSICAL_DEVICE`: a user-supplied physical-device record. Brain does not discover or connect to a device automatically.

For economics, `power_cost` is the supplied electricity rate in JOD/kWh. The caller can override it when calling `analyze_economics`; neither value is fetched from a utility or provider.

Remote/physical telemetry can be recorded as untrusted evidence supplied by a caller. Hash verification proves only that the local evidence payload has not changed; the release gate remains blocked pending independent provider/device identity attestation. The adapter does not make network calls, provision hosting, execute mining, or request wallet material. Economic results use supplied inputs and remain unverified estimates.

Example (simulation only):

```python
from brain_v12.brain.asic_resource_adapter import ASICResource, ASICResourceAdapter

brain = ASICResourceAdapter()
brain.register(ASICResource(
    "simulator-01", execution_mode="SIMULATOR", hashrate=100,
    hashrate_unit="TH", power_watts=3000,
))
report = brain.simulate("simulator-01", duration_seconds=60)
```

## Preflight

Prepare a JSON file from a candidate provider's published terms. Do not include passwords, API tokens, seed phrases, private keys, or account recovery data.

```bash
python tools/brain_asic_hosting_preflight.py --offer offer.json --output artifacts/brain-asic-hosting-preflight.json
```

Required fields:
- `operator_legal_name`
- `facility_evidence_url` (HTTPS)
- `public_pool_or_payout_evidence_url` (HTTPS)
- `trial_terms_url` (HTTPS)
- `trial_hashrate_ths` (positive number)
- `upfront_cost_usd`, `deposit_required_usd`, `recurring_cost_usd`, `withdrawal_fee_usd`, `activation_fee_usd` (all zero)
- `trial_rewards_withdrawable: true`
- `requires_paid_upgrade_to_withdraw: false`
- `requires_referrals_to_withdraw: false`
- `requires_wallet_seed_or_private_key: false`
- `physical_asic_disclosed: true`
- `external_wallet_payout_supported: true`

Example shape (fill only from published provider terms):

```json
{
  "operator_legal_name": "",
  "facility_evidence_url": "",
  "public_pool_or_payout_evidence_url": "",
  "trial_terms_url": "",
  "trial_hashrate_ths": 0,
  "upfront_cost_usd": 0,
  "deposit_required_usd": 0,
  "recurring_cost_usd": 0,
  "withdrawal_fee_usd": 0,
  "activation_fee_usd": 0,
  "trial_rewards_withdrawable": false,
  "requires_paid_upgrade_to_withdraw": true,
  "requires_referrals_to_withdraw": true,
  "requires_wallet_seed_or_private_key": true,
  "physical_asic_disclosed": false,
  "external_wallet_payout_supported": false
}
```

## Fail-closed policy

- `BLOCKED`: a required fact is missing, a cost is nonzero, or withdrawal/security conditions are unsafe.
- `NEEDS_MANUAL_REVIEW`: the input fields satisfy the structural checks; this is not an endorsement, proof of provider legitimacy, or approval to activate.
- Automatic activation remains disabled. This tool does not make network requests, provision resources, connect a mining pool, handle wallets, make payments, or claim that mining has begun.
- Any real activation requires a separately reviewed provider agreement and explicit user approval. Never send funds to "unlock" trial earnings.

## Acceptance criterion for real income

Only count revenue after an independently verifiable BTC payout reaches the user's own wallet. Keep estimated rewards, dashboard-only trial balances, and provider promises separate from realized revenue.

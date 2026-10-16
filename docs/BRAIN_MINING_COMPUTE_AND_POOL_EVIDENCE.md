# Brain-owned compute preflight and independent pool evidence

## Safety boundary

This implementation does **not** enable live mining. It adds a fixed SHA256d known-answer preflight and a read-only Braiins Pool workers collector. No nonce search is invoked by the API preflight; no Stratum session is opened; no share is submitted; no worker or pool configuration is changed; no payout endpoint is queried; and no wallet is accessed.

## Compute gate

- `GET /api/mining-node/compute-preflight` runs only the known-answer `SHA256d("abc")` test.
- The bounded SHA256d library exists, but this is not a production mining service.
- The preflight always reports `execution_allowed=false` and `execution_started=false`.
- Live execution remains blocked until a Brain-owned compute host is independently attested, the resource budget is verified at zero cost, a reviewed pool submission adapter exists, and separate explicit authorization/review is completed. Android/Termux devices remain connectivity/observation gateways, not compute hosts.
- `GET /api/mining-node/readiness` keeps live mining, pool shares, payout, and profit blocked.

## Independent Braiins Pool telemetry

The read-only collector uses the documented HTTPS endpoint `https://pool.braiins.com/accounts/workers/json/btc` with the `Pool-Auth-Token` header. It makes one GET request, verifies TLS using HTTPX defaults, rejects redirects and unexpected origins, limits the response size, matches an explicitly configured worker ID, validates finite/non-negative metrics, and checks that the last pool share is recent. It does not query payout/profile endpoints.

Run the doctor only when an already-authorized **read-only** Braiins API token and the exact worker name are available in the execution environment:

```powershell
# First load the existing read-only API token from your protected secret store
# into BRAIINS_POOL_API_TOKEN, and set BRAIINS_POOL_WORKER_ID to the exact worker name.
python brain_v12/tools/brain_braiins_pool_evidence_doctor.py
```

Do not paste the token into source control, command history, an issue, or chat; do not generate a new key as part of this change. The collector never prints the token. It does not run automatically during tests or server startup. Its test suite uses a fake HTTP client and makes no external requests.

`POOL_ACTIVITY_OBSERVED` means the authenticated pool API reported a matching worker with positive 5-minute hashrate/share counters and a recent last-share timestamp. It is **aggregate pool-side telemetry**, not proof that Brain produced the work and not a cryptographic proof of any individual accepted-share submission. The collector deliberately leaves `brain_runtime_activity_verified`, `accepted_share_submission_verified`, `payout_verified`, and `revenue_verified` false.

## Endpoints

- `GET /api/mining-node/status`: software-only contract and gate state.
- `GET /api/mining-node/readiness`: separate primitive, host, pool-share, payout, and profit gates.
- `GET /api/mining-node/compute-preflight`: offline known-answer self-test only.
- `GET /api/mining-node/pool-evidence/status`: collector capabilities; performs no network call and does not inspect credentials.

## Tests

The focused test set covers the mining-node API, SHA256d primitive, evidence schema, mocked Braiins collection, wrong worker/origin, redirects, non-200 responses, stale telemetry, zero shares, NaN/Infinity/boolean metrics, and the requirement that pool activity never implies Brain-runtime activity or revenue.

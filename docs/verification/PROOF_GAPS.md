# Electronic Brain — Proof Gap Register

## Scope

This is a bounded repository-level status note, not a complete external-system audit. The shared proof evaluator, registry, tests, and focused workflow already exist on `main`. This document does not claim that any live external source has been authenticated.

## Evidence status

| Domain | Current evidence boundary | Status |
|---|---|---|
| Software proof evaluator | Code and focused unit tests exist; inspect current workflow run for the exact commit before claiming current CI is green | Implemented; CI-bound |
| Live mining pool | Must show authenticated worker, positive pool-observed hashrate, and accepted shares | BLOCKED until fresh pool-origin evidence |
| Realized mining revenue | Requires independent payout and blockchain reconciliation | BLOCKED until independently verified |
| ASIC RTL/synthesis | GitHub Actions run #255 completed successfully on commit `49c6966e280d7f2a8b5e94985ddb97a667292baf`; SHA-256/SHA256d synthesis and control-shell steps succeeded and build evidence was published | CI synthesis evidence only |
| Physical GDSII / signoff | Must inspect actual artifact and relevant physical-design reports | Not established by RTL synthesis alone |
| Foundry acceptance / silicon manufacture / silicon test | Requires independent foundry/manufacturing/test evidence | BLOCKED until such evidence exists |
| Device execution | Requires fresh authenticated heartbeat plus task result and postcondition | Not established by repository CI alone |
| Revenue/profit | Requires actual reconciled transactions and costs | Not established by software tests or forecasts |

## Mining acceptance checklist

1. Confirm the pool endpoint and worker identity through a safe, authenticated, read-only path.
2. Capture timestamped pool-origin worker telemetry.
3. Verify positive hashrate over a meaningful observation interval.
4. Verify accepted shares reported by the pool, distinct from locally generated or simulated shares.
5. Reconcile any payout separately against provider and blockchain evidence.
6. Keep revenue/profit unverified until reconciliation succeeds.

No secrets should be printed, committed, or requested in logs. Do not enable paid resources, wallets, withdrawals, or production execution merely to satisfy a test.

## Next actions

1. Preserve the current-main synchronization idempotency fix and its successful CI evidence.
2. Keep proof-gate code and documentation aligned to current `main`, rather than merging stale branches wholesale.
3. Connect one read-only evidence adapter at a time and test stale, duplicate, conflicting, synthetic, and malformed evidence.
4. Inspect the actual ASIC build artifacts and their hashes before making any stronger physical-design claim.
5. Keep live mining and revenue claims blocked until independently sourced evidence is available.

## Explicit non-claims

- A successful CI run is not proof of physical ASIC silicon.
- RTL synthesis is not proof of a fabricated or operating miner.
- A read-only telemetry payload is not proof of Brain-owned execution, accepted shares, payout, or profitability.
- A successful control-plane test is not a live pool connection.

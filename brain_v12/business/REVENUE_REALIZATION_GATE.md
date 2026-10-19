# Revenue Realization Evidence Gate

This module is a fail-closed ledger boundary, not proof that a payment or worker is real by itself.

## Acceptance requirements
- Worker evidence must identify a completed real execution and match task/opportunity.
- Accepted delivery must reference the same execution, task and opportunity.
- Payment must be independently verified, settled, and match order/task/opportunity, exact amount and currency.
- Simulation/demo/test/fixture/mock evidence is rejected.
- SQLite unique constraints make realization idempotent by request key and provider transaction ID.
- Costs live in a separate table and summary; they do not inflate or reduce gross revenue.
- The trusted caller must verify provider signatures/API status and worker evidence provenance before passing evidence to this gate.

## Usage
Construct `RevenueRealizationGate(path)`, then call `realize(task=..., worker=..., delivery=..., payment=..., idempotency_key=...)`.
Only a successful result returns `REVENUE_REALIZED`. A matching retry returns the existing ledger ID with `duplicate=true`; conflicting duplicate keys/transactions fail closed.

## Important boundary
This does not deploy a worker, call PayTabs, prove a live payment, or claim any revenue has been collected. Those claims require production deployment and independently inspectable provider evidence. Do not pass browser return URLs, self-asserted payment fields, CI status, or synthetic fixtures as independently verified payment proof.

## Activity-first recording (separate from revenue realization)

Mining activity must not be discarded just because payout proof is absent. Use
`record_activity(activity=..., idempotency_key=...)` to append a separately
idempotent activity record for observed hashrate, SHA-256d experiments, share
counters, mining sessions, or simulator runs. Activity records and estimates
remain separate from the `realized_revenue` table.

- Activity is labelled with its mode (`live`, `simulation`, `test`, or
  `unknown`) and reported activity status. Simulation data remains simulation.
- Optional estimated earnings are stored separately and summarized under
  `estimated_earnings_unverified`; summaries retain currency, execution mode, and
  activity status so simulated estimates are not aggregated with live observations.
  Estimate amounts are returned as exact decimal strings (not binary floating-point
  totals) so small BTC amounts such as one satoshi are not rounded away. They never
  increase realized revenue.
- A record without independent payment proof returns
  `payment_status=PAYMENT_UNVERIFIED` and `revenue_status=NOT_REALIZED`.
- Accepted-share counters are activity telemetry, not proof of a payout.
  Hashrate and SHA-256d results do not independently prove real pool mining.
- `realize()` remains the only path that writes to realized revenue and still
  requires independently verified, settled payment evidence plus matching
  production task, worker, delivery, amount, currency, and transaction linkage.
- Activity idempotency prevents duplicate retries from multiplying records;
  conflicting payloads under the same key fail closed.

Thus the gate rejects unsupported *revenue promotion*, not the recording of
useful work, telemetry, simulation output, or unverified estimates.

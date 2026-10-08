# Economic Autonomy Layer

The Brain economic subsystem now has a deterministic integrity path:

source/opportunity
-> verification
-> decision/governor
-> work/delivery
-> payment evidence
-> evidence integrity
-> causal proof
-> settlement
-> audit
-> ledger rebuild
-> economic memory.

## Hard boundaries

- An opportunity is never revenue.
- A target is never revenue.
- Expected value is never revenue.
- Revenue requires valid payment evidence.
- Evidence IDs and evidence fingerprints cannot be settled twice.
- A settlement must have a complete opportunity/application/task/delivery/payment causal chain.
- Ledger totals are rebuildable from settlement events.
- The economic governor is single-path and side-effect free.
- The governor does not submit applications, move money, or fabricate evidence.
- Self-healing must never rewrite a financial fact to repair an integrity failure.

## First revenue milestone

The initial objective is USD 0.10. It remains a target until a valid payment proof is settled.

Current confirmed revenue remains USD 0.00 until such evidence exists.

## Recovery model

If a stored ledger disagrees with replayed settlement events, the system should report an economic integrity failure rather than silently changing the balance.

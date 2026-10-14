# Bitcoin Digital Lab — Cloud-Only Operating Mode

## Decision

This project must not depend on a phone, Termux device, desktop, or remote agent being available. The cloud-only lab runs software validation on GitHub-hosted CI. It never starts a live miner and never connects to a mining pool.

## What CI can prove

- Python modules compile.
- The double-SHA-256 primitive matches a deterministic test vector.
- Mining-economics, API, and worker guardrail unit tests pass.
- An evidence-boundary artifact is produced for each run.

These are software-quality results only. The SHA-256d vector test is not a Bitcoin block search, and a successful CI job is not a mining result.

## What remains unproven

Without a separately authorized and suitable compute resource, the lab cannot prove:
- a live Stratum pool session or pool-side authorization;
- pool-measured hashrate or accepted shares;
- physical ASIC hardware or fabricated silicon;
- Bitcoin payout or realized revenue.

GitHub-hosted CI is for tests only. Do not run cryptocurrency mining in CI. No paid resource should be provisioned automatically.

## Status vocabulary

- `PASS`: a specific software test passed.
- `NOT_RUN`: a live or physical gate was not attempted.
- `NOT_VERIFIED`: evidence is insufficient to assert success.
- `VERIFIED`: reserved for independently checkable evidence from the system that owns the fact (for example, pool-side share records or a transaction record).

Never promote a simulated node, test fixture, miner stdout line, estimated revenue, or successful workflow into proof of real mining or income.

## Current path

Use the **Bitcoin Digital Lab (Cloud-Only, No Live Mining)** workflow to validate code and retain the evidence-boundary artifact. The separate Termux worker remains optional legacy/device-specific code; it is not a prerequisite for cloud CI and must not be described as deployed while no device is available.

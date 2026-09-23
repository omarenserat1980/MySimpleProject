# Electronic Brain — Autonomous Architecture

## Goal
Build a continuously improving external runtime that researches, plans, builds,
tests, measures and pursues legitimate revenue opportunities while keeping
financial, legal, credential and destructive actions behind explicit approval.

## Closed loop
1. Observe code, capabilities, market evidence and previous outcomes.
2. Plan one bounded development or revenue experiment.
3. Execute only allowlisted, reversible operations.
4. Verify using tests, source evidence, or actual payment records.
5. Store the evidence and outcome.
6. Re-rank the next action.
7. Repeat on an externally controlled schedule.

## Capability growth
The self-development engine tracks domains such as finance, banking, markets,
trade, crypto, stocks, mathematics, statistics, computer science, cybersecurity,
science, engineering, compliance and communication. A domain is not considered
mastered merely because it is listed.

## Earnings truth
Internal JOD estimates are hypotheses. Revenue is counted only when a ledger
entry has a PAID or VERIFIED_PAID status and a positive amount.

## Safety boundary
The runtime cannot grant itself permissions. It must never autonomously:
- move or withdraw money
- trade real money
- borrow money
- sign contracts
- read or rotate secrets
- perform destructive repository operations
- make irreversible legal commitments

Publishing, sending messages, submitting paid work, spending money and production
changes remain approval-gated unless the host application explicitly defines a
separate authorization policy.

## External worker
worker.py is designed for a user-controlled VPS, PC or Termux environment. It is
bounded by cycle count, has a stop-file, and writes an audit chain. It is not a
hidden background process inside ChatGPT.

## Recovery
Keep CI tests enabled. On failure, stop promotion and preserve evidence. Use the
STOP_BRAIN file to stop the worker.

## CI status
Repository-root GitHub Actions regression workflow is enabled for brain_v7 changes.

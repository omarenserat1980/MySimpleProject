# Brain Local Executor (Termux-first)

A local-first, zero-network task runner to reduce reliance on external remote-desktop tooling. It runs only fixed, allowlisted actions and never evaluates arbitrary shell commands.

## Safety contract

- No network calls, GitHub pushes, node registration, node activation, mining, or mining-pool connections.
- status reads Git status; test-measurement runs the measurement unit tests; test-local-executor runs the executor's own tests; measure writes a uniquely named read-only local measurement JSON without overwriting prior evidence; verify-evidence checks every matching evidence file against fail-closed safety gates.
- Evidence verification is only a local schema/safety-contract check. It does not prove device identity, hardware attestation, or independent verification.
- Queue state is local. Audit events form a SHA-256-linked sequence for tamper-evident diagnostics, not a trusted digital signature or external timestamp.
- Tasks stop on first failure; batches are limited to 20 tasks. No automatic retries or parallel execution.

## Usage

Run from the repository root in Termux:

    python -m brain_phone_base.local_executor list-actions
    python -m brain_phone_base.local_executor --repo . enqueue test-measurement
    python -m brain_phone_base.local_executor --repo . run-next
    python -m brain_phone_base.local_executor --repo . enqueue test-local-executor
    python -m brain_phone_base.local_executor --repo . run-next
    python -m brain_phone_base.local_executor --repo . enqueue verify-evidence
    python -m brain_phone_base.local_executor --repo . run-next
    python -m brain_phone_base.local_executor --repo . queue

Runtime queue and audit files are written under .brain_local_executor/. This folder is local state and should not be committed as measurement evidence. Review git status before committing code changes.

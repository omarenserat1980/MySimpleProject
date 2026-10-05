# Brain Execution Fabric

The Brain execution architecture is capability-oriented and Brain-owned.

## Runtime layers

1. Brain Scheduler / Task Engine
2. Execution Fabric
3. Capability Registry
4. Durable Queue
5. Worker Lease
6. Worker execution
7. Verification
8. Evidence
9. Recovery / reconciliation

## Worker types

Workers are replaceable implementations, not authorities:

- local runtime
- Termux / Android
- Linux
- Windows
- QEMU
- GPU
- media worker

A worker may execute only capabilities for which it is registered and currently online. No worker may silently redirect work to GitHub-hosted CI.

## Failure semantics

No suitable worker returns NO_BRAIN_WORKER_FOR:<capability>.

An unverified internal runtime returns BRAIN_INTERNAL_RUNNER_NOT_VERIFIED.

Both are blocking states. They are never success and never trigger an implicit external fallback.

## GitHub role

GitHub may provide source control, audit, workflow verification, artifacts and synchronization. It is not part of the minimum execution path.

## Independence test

A future integration is considered Brain-independent only when the same task can be queued, executed, verified, checkpointed and recovered while GitHub is unavailable.

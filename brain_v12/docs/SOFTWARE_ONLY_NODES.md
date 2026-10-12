# Software-only execution nodes

Electronic Brain uses software nodes as its default execution resources. A node is
registered through the existing `WorkerRegistry` and advertises a worker ID,
kind, capabilities, and a time-limited lease. Routing still uses the existing
`WorkloadRouter` and `WorkloadController`; this change does not add a parallel
orchestrator.

## Physical-device adapter boundary

Physical-device / Termux agents are optional compatibility integrations. They are
disabled by default and are not required to initialize the registry or execute
software-node unit tests. To explicitly enable legacy device routing, set
`BRAIN_ENABLE_DEVICE_WORKERS=1`. This opt-in does not make a device available
unless its adapter reports a fresh online heartbeat.

An optional adapter exception is treated as adapter unavailability and does not
take down software-node registry operations.

## Resource and verification limits

Software-node registration is not proof that a task has executed. A valid lease
only describes availability. Execution success still requires the executor's
actual result and the existing verification/evidence gates. Virtual CPU, memory,
storage, network, power, and thermal figures are simulations unless independently
calibrated. Hosted GitHub runners are finite and subject to repository plan,
quota, and workload constraints.

## Focused verification

Run from the repository root:

```bash
PYTHONPATH=. pytest -q brain_v12/test_worker_registry.py
```

The dedicated GitHub Actions workflow runs this focused suite on a GitHub-hosted
Ubuntu runner and does not require Termux, Android, Windows, Hyper-V, QEMU/KVM, or
a self-hosted runner.

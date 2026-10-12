# Software-only execution nodes

Electronic Brain routes workloads only to registered software workers. A node is
registered through the existing `WorkerRegistry` and advertises a worker ID,
kind, capabilities, and a time-limited lease. Routing continues to use the
existing `WorkloadRouter` and `WorkloadController`; no parallel orchestrator is
introduced.

## Hardware removal policy

Physical-device, Android, Termux, and PC-specific workers are disabled, not merely
disabled by default. The legacy `include_device_adapters=True` argument is
accepted for compatibility but cannot enable discovery. Registering a worker
with kind `device`, `physical`, `termux`, `android`, or `hardware` fails
closed with `PHYSICAL_DEVICE_WORKERS_DISABLED`. Brain must not require Arkan,
Redmi, Realme, Hyper-V, or any user-owned host to initialize or route software
workloads.

This change removes these devices from Brain's execution registry; it does not
delete or alter the user's machines, revoke external accounts, or erase historical
diagnostic files. Legacy/manual hardware workflows must not be used as the default
execution path.

## Resource and verification limits

Software-node registration is not proof that a task has executed. A valid lease
only describes availability. Execution success still requires the executor's
actual result and the existing verification/evidence gates. Virtual CPU, memory,
storage, network, power, and thermal figures are simulations unless independently
calibrated. Software-only does not mean unlimited compute; hosted runners remain
subject to quota and workload constraints.

## Focused verification

Run from the repository root:

```bash
PYTHONPATH=. pytest -q brain_v12/test_worker_registry.py
```

The dedicated GitHub Actions workflow runs this focused suite on a GitHub-hosted
Ubuntu runner and does not require Termux, Android, Windows, Hyper-V, QEMU/KVM, or
a self-hosted runner. It also runs a clean-environment preflight, removing device
and agent environment variables and checking application import, core routes, and
the health contract. This is an import/startup smoke test, not proof that every
workload or external integration has migrated.

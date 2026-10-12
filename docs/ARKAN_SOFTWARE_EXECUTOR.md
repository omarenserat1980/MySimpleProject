# Arkan Software-Only Executor

## Scope and truth boundary

The executor runs Brain's existing symbolic CPU simulator as a software-only node
named \`arkan-virtual-01\`. It reuses \`VirtualTaskQueue\` and
\`DurableTaskStore\` rather than creating a second queue implementation.

- Tasks and results are stored in a local SQLite database.
- A restarted process reconstructs active tasks from SQLite. A task left in
  \`RUNNING\` by a lost process is conservatively requeued and its attempt count
  increases when claimed again.
- A maintenance thread periodically invokes expired-lease recovery and pumps
  queued work while the process is alive.
- Task admission is allowlisted (\`cpu_smoke\`, \`self_test\`); arbitrary shell
  commands and arbitrary code are not accepted by this service.
- Node status is atomically written to \`state.json\` and labels execution as
  \`SIMULATED\`.
- The service never probes or allocates physical hardware and does not require
  Desktop Commander.

**Persistence is local, not cloud replication.** The SQLite database and state
file survive a process restart only if the chosen runtime directory survives.
A service manager can restart the process after an exit, but availability still
depends on the host, filesystem, and service manager being available. GitHub
hosted runners are ephemeral and are not used as a permanent daemon host.

The service does not install or boot Windows Server 2025. The state report must
continue to show \`NOT_INSTALLED\`, \`NOT_VERIFIED\`, and
\`native_os_boot_verified=false\`.

## Run locally on a compatible Python host

From the repository root:

\`\`\`bash
python -m unittest brain_v12.tests.test_arkan_software_executor -v
python -m brain_v12.brain.arkan_software_executor submit --task-type cpu_smoke --idempotency-key manual-smoke-001
python -m brain_v12.brain.arkan_software_executor status
python -m brain_v12.brain.arkan_software_executor serve
\`\`\`

The default state root is \`~/.brain/runtime/arkan-software-node\`. Override it
with \`BRAIN_ARKAN_SOFTWARE_ROOT\` or the CLI \`--root\` option. Keep this path on
a writable persistent disk and include it in the backup plan.

## Linux user service

\`deploy/arkan-software-node.service.example\` is a user-level systemd unit
template. Review and edit \`WorkingDirectory\` and Python paths before installing.
It uses \`Restart=on-failure\` and writes only beneath the user's runtime root.
Systemd is not available on every environment (including typical Termux setups);
on those platforms, use the platform's supported process supervisor. Do not
claim a daemon is running until service status and heartbeat evidence are checked.

## Acceptance checks

The automated tests verify:
1. allowlisted task execution and durable result lookup after reconstructing the service;
2. rejection of an unapproved task type;
3. recovery of a simulated interrupted \`RUNNING\` task after restart;
4. idempotent submissions using the same idempotency key;
5. truthful simulation-only identity and Windows boot fields.

This is a persistent local software executor implementation, not proof of a
currently deployed 24/7 service. Deployment, process supervision, backups, and
external availability must be verified separately.

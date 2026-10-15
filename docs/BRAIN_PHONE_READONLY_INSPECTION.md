# Brain Phone — read-only resource inspection

This adds a strictly local, read-only inspection path alongside the existing
simulation-first Brain Phone Base.

## Run

From the repository root, or from the checked-out repository in Termux:

```bash
python -m brain_v12.tools.brain_phone_readonly_inspector --node-id realme-local-check
python -m unittest brain_v12.tests.test_brain_phone_readonly_inspector -v
```

Run the command on the phone you want to inspect. It measures the environment
where Python is running. Running it on a PC measures that PC, not a phone.

## Evidence labels

- `mode=READ_ONLY_LOCAL_MEASUREMENT`
- `state=MEASURED_LOCAL_UNVERIFIED`
- `synthetic=false`
- `measurement_source=LOCAL_OS_SELF_REPORTED`
- `resource_metrics_are_self_reported=true`

The inspector reads OS-reported CPU count, available memory, disk usage,
architecture, Python version, and load average where supported. These are local
measurements, not independent hardware attestation or proof of a remote device.

## Safety guarantees

The inspector does not make network calls, send a heartbeat, register a device,
activate a node, dispatch tasks, start mining, connect to a mining pool, or
claim mining/revenue verification. It does not read credentials. Mining and
pool connection indicators are explicitly false in its output.

Keep simulator fixtures and local readings separate: do not relabel simulated
metrics as measured, or treat self-reported local readings as verified capacity.
Tests establish code behavior only; they do not prove that a physical phone was
inspected. No automatic mining or pool connection is part of this change.

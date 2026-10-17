# Brain Micro-Executor: reduce Desktop Commander usage

## Purpose

Use a small, local, read-only preflight before spending a Desktop Commander call
on routine repository/device inspection. The first increment is intentionally
diagnostic-only and runs on Python 3.10+ (including Termux Python).

## Current scope

Run from the repository root:

```bash
python brain_v12/tools/brain_micro_executor_doctor.py
python brain_v12/tools/brain_micro_executor_doctor.py --json
```

The tool checks the Python runtime, detects whether it is running in Termux,
locates the repository, and reports whether key runtime/bridge/policy files exist.
It does not read or print credentials, make network requests, poll or execute
tasks, register a worker, edit files, or change production settings.

## MicroDroid distinction

Android MicroDroid is a minimal Android guest environment associated with the
Android Virtualization Framework; it is not interchangeable with Termux and
cannot be assumed available on a given phone. This repository increment does not
claim to install, launch, or verify MicroDroid. Hardware/virtualization support
must be established separately with device-origin evidence.

## Canonical Brain policy

The canonical runtime remains software-only. The micro-executor is a local
maintenance/diagnostic helper, not a registered Android/Termux workload worker.
It must not bypass `PHYSICAL_DEVICE_WORKERS_DISABLED`, authorization gates,
verification gates, or evidence requirements. GitHub-hosted software runners
remain the preferred execution path for repository tests.

## Next bounded steps

1. Run the read-only doctor on the target phone and retain its JSON output.
2. Add focused unit tests for the doctor on a hosted runner.
3. Move only repeatable, low-risk diagnostics into this helper.
4. Consider optional local actions only behind explicit allowlists and dry-run
   defaults; never add arbitrary command execution or secret export.
5. Keep Desktop Commander for tasks requiring interactive UI, device permissions,
   or independent observation that local scripts cannot provide.

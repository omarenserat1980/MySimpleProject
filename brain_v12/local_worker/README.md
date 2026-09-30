# Brain Local Worker Bridge

Provider-neutral local worker for a user-owned Brain host or BRAIN Termux Emulator environment.

## Contract
- Watches a local queue directory for JSON jobs.
- Claims each job by atomic rename into `running/`.
- Executes only an explicit allowlist of safe local operations.
- Writes evidence to `completed/` or `failed/`.
- Never moves money, publishes externally, signs transactions, changes policy, or executes arbitrary shell commands.
- Queue paths are configurable with `BRAIN_LOCAL_WORKER_ROOT`; default is `brain6_artifacts/local_worker`.

This is the local execution adapter for the Brain Cloud worker protocol. It does not require Oracle Cloud, Google Cloud, Render, or a paid API.

## Run

```bash
python3 brain_v12/local_worker/brain_local_worker.py
```

Supported jobs:
- `python_version`
- `platform`
- `brain_home`
- `ffmpeg_version`
- `ffprobe_version`
- `filesystem_probe`

A real long-running host is still required for continuous execution.

# Brain Native Home Server Runtime

This runtime is Brain-owned and local-first. It does not provision Azure, depend
on Render as an executor, or use GitHub Actions as an execution backend.

## Components

- `brain/internal_task_runtime.py`: durable append-only queue, task state and
  per-task evidence files.
- `brain/internal_worker.py`: local worker process that consumes queued work
  on the machine where it is started.
- `brain/execution_gateway.py` and `brain/internal_runner.py`: execution
  authority and fail-closed runner preflight.
- `/api/brain/internal-runtime/status`: runtime and local runner readiness.
- `POST /api/brain/internal-runtime/probe/python-version`: queues only the
  fixed, harmless `python --version` probe; it does not execute the probe.
- `POST /api/brain/internal-runtime/run-one`: loopback-only API fallback for
  one task. A hosted remote caller is rejected; prefer the local worker.

## Run the worker on the intended home-server device

From the repository root, with the existing Brain environment and dependencies
installed:

```sh
python -m brain_v12.brain.internal_worker --once
```

For continuous processing:

```sh
python -m brain_v12.brain.internal_worker
```

The worker writes task evidence below
`brain_v12/.brain/internal_runtime/evidence/` by default. To put the queue and
evidence on persistent storage, set `BRAIN_INTERNAL_RUNTIME_ROOT` to an absolute
directory on that device before starting both the Brain API and worker.

## Safe activation sequence

1. Start the Brain API locally on the intended home-server device.
2. Check `GET /api/brain/internal-runtime/status`; the internal runner must
   report `ONLINE` with verified preflight.
3. Queue the Python version probe using the authenticated control API.
4. Run the worker with `--once` and inspect its JSON output and evidence file.
5. Only after this succeeds, register the device as an online Brain worker and
   assign more capabilities.

The status endpoint is diagnostic, not proof of a physical server being online.
A successful task requires a `COMPLETED` result and saved evidence. If preflight
fails, the task must be treated as blocked, not successful. No secrets should be
placed in source control or pasted into chat.

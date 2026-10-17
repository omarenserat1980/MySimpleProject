# Brain Home Server (initial runtime)

This is a local-first, SQLite-backed task bridge intended for a computer you control. It does not replace the existing Brain API or deploy anything to Render.

## Start locally

From the repository root, install the repository's existing requirements, then run:

```bash
uvicorn brain_v12.home_server:app --host 127.0.0.1 --port 8765
```

Binding to `127.0.0.1` keeps the first run local to that computer. Do not expose this service to the public internet without a separately reviewed network and authentication configuration.

## Configuration

- `BRAIN_HOME_SERVER_DB` (optional): SQLite database path. Default: `~/.brain/home-server.sqlite3`.
- `BRAIN_CONTROL_KEY` (required for task creation/listing): reuse an already-authorized control key. This service never generates or prints a key.
- `BRAIN_AGENT_KEY` (or existing compatibility aliases `BRAIN_EMULATOR_KEY`, `BRAIN_EMULATOR_AGENT_KEY`, `TERMUX_AGENT_KEY`) for worker claim/report calls. Worker credentials are kept separate from the control key. If the appropriate key is absent, that API fails closed with HTTP 503.

## Endpoints

- `GET /health`: basic process health.
- `GET /api/home-server/status`: database/queue counts and whether control auth is configured; never returns the key.
- `GET /api/home-server/tasks`: authenticated queue inspection.
- `POST /api/home-server/tasks`: authenticated enqueue; optional idempotency key.
- `POST /api/home-server/claim`: authenticated worker lease.
- `POST /api/home-server/tasks/{task_id}/report`: authenticated worker result.

Only `status`, `python_version`, `platform`, and `brain_self_test` task names are accepted. The bridge queues task descriptions; it does not execute arbitrary commands. A worker implementation and integration with the existing Brain runtime remain separate steps.

## Verify

```bash
python -m unittest brain_v12.tests.test_home_server -v
```

The tests cover idempotent enqueue, lease ownership, allowlisted task names, and recovery of expired leases. Local tests do not establish that Arkan, Redmi3, GitHub, or Render are connected.

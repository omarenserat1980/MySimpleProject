# Brain Home Server: first-task verification

This guide is for a controlled, harmless diagnostic. It does not deploy the service, change environment variables, or modify a device.

## Gate 1 — verify the live app

Open the deployed service's `/openapi.json` and confirm that it lists all of these paths:

- `POST /api/home-server/tasks`
- `GET /api/home-server/tasks`
- `POST /api/home-server/claim`
- `POST /api/home-server/tasks/{task_id}/report`

If these routes are absent, stop. A branch containing the code is not proof that the running service has it.

## Gate 2 — confirm existing configuration

The control API expects the already-configured `BRAIN_CONTROL_KEY`. Worker authentication accepts one of the server-side variables `BRAIN_AGENT_KEY`, `BRAIN_EMULATOR_KEY`, `BRAIN_EMULATOR_AGENT_KEY`, or `TERMUX_AGENT_KEY`. The worker's local key file must match the configured worker key. Do not put key values in Git, tickets, chat, or logs, and do not create or rotate keys as part of this procedure.

## Gate 3 — enqueue a harmless task

Using an authorized private API client, send a JSON request to `POST /api/home-server/tasks` with this body:

```json
{
  "task": "python_version",
  "params": {},
  "priority": 1,
  "required_capabilities": ["python"],
  "idempotency_key": "first-python-version-check-v1"
}
```

The request must use the existing control credential in the HTTP Authorization header. Keep credentials out of command history and output. Record the returned `task.task_id`.

## Gate 4 — verify the result

Use the same authorized control client to request `GET /api/home-server/tasks?limit=10`. The task must progress from `QUEUED` to `CLAIMED` and then `COMPLETED`. A completed result should contain the worker's Python version and executable path.

The worker must be started deliberately on the intended device with `BRAIN_HOME_SERVER_URL` pointing to the origin that passed Gate 1. The default worker key file is `~/v12-agent/agent.key`; do not print its contents. The worker is outbound-only and accepts only the fixed diagnostics `status`, `python_version`, `platform`, and `brain_self_test`.

## Error interpretation

- `404`: wrong origin or the live app does not include the router.
- `503 HOME_SERVER_CONTROL_NOT_CONFIGURED`: control authentication is not configured server-side.
- `503 HOME_SERVER_WORKER_AUTH_NOT_CONFIGURED`: worker authentication is not configured server-side.
- `401`: the credential is missing or does not match the required role.
- `IDLE`: no queued task matches the worker's capabilities.
- `409`: worker identity or lease does not match the task report.

## Evidence boundary

Automated tests cover the queue and a mocked claim/execute/report cycle. They do not prove a real device is connected. Do not trigger deployment, alter service configuration, provision cloud resources, or change device permissions without explicit authorization.

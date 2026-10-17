# Brain Cloud Worker Deployment Gate

This checklist is intentionally fail-closed. Passing CI proves that the image builds and the local smoke test works; it does not prove a public deployment, continuous uptime, task execution, mining, or revenue.

## Before deploying

- [ ] Choose a host that the project owner controls and that can remain online. GitHub-hosted Actions runners are ephemeral and are not a 24/7 service.
- [ ] Confirm the host can run the repository's .NET 10 container and expose the configured HTTP port.
- [ ] Configure persistent writable storage for `BRAIN_HEARTBEAT_PATH` and `BRAIN_WORKER_REGISTRY_PATH`; defaults under `/var/lib/brain` require appropriate permissions.
- [ ] Store `BRAIN_CLOUD_API_KEY` in the host's secret manager/environment, never in Git. Until the command queue is implemented, a configured key does not make commands executable.
- [ ] Do not publish an origin or update `BRAIN_ORIGIN` before independent HTTPS health and readiness checks succeed.
- [ ] Verify the deployed image digest and record the deployment revision.

## Post-deployment checks

1. Request `GET /healthz`. HTTP 200 confirms only that the HTTP process responds.
2. Request `GET /readyz`. Require HTTP 200 and `ready: true`; HTTP 503 is a deployment/readiness failure.
3. Request `GET /health` and `GET /api/brain/status` to inspect recent pulses. Do not infer worker registration or real-world work from an HTTP 200 alone.
4. Restart the service and verify it recovers without losing its persisted heartbeat/registry files.
5. Stop or deliberately fault a test worker in a non-production environment and confirm readiness becomes false.
6. Confirm command submission remains unavailable until a durable task queue and verified executor are implemented and tested.

## Evidence required for claims

| Claim | Minimum evidence |
|---|---|
| Image builds | Successful CI build and container build |
| Service is reachable | External request to the deployed HTTPS endpoint |
| Service is ready | External `/readyz` response with all required checks passing |
| Continuous operation | Time-stamped uptime/heartbeat observations across the claimed period |
| Task executed | Durable task ID plus executor result and integrity-checked evidence artifact |
| Real mining | Independent pool-side worker telemetry and accepted-share evidence |
| Revenue realized | Pool/account payout or transaction evidence; hashrate estimates are not revenue |

## Current known limitation

`POST /api/brain/command` currently returns `501 COMMAND_EXECUTION_NOT_CONNECTED` after authentication. This is deliberate: the endpoint is not connected to a durable queue or verified execution adapter. Do not remove this guard by simply returning HTTP 200. Implement and test the queue, bounded task schema, authorization policy, audit trail, idempotency, and evidence persistence first.

## Safety boundary

This checklist does not authorize production changes, secret rotation, live mining, external publishing, or financial actions. Each requires its own explicit authorization and independent verification.

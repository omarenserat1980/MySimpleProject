# Brain physical-worker connection and authentication preflight

This procedure checks connectivity; it does not start a miner, send a heartbeat, or prove pool-side mining.

## Required configuration on the worker host

Set these values in the host's environment or secret manager, not in source control:

- `BRAIN_MINING_API_URL`: the HTTPS base URL of the running Brain API (no trailing path).
- `BRAIN_MINER_STATS_URL`: the miner's read-only stats URL. Plain HTTP is allowed only for loopback addresses such as `http://127.0.0.1:PORT/stats`.
- `BRAIN_MINING_WORKER_API_TOKEN`: a random secret of at least 32 characters, configured identically in Brain's runtime and the worker host.
- `BRAIN_MINING_WORKER_ID`: a stable non-secret identifier, configured for the telemetry agent.

Generate a token locally with Python, then place it directly into the deployment's secret store/environment. Never send it in chat, commit it, print it in CI logs, or place it in a URL. Example local generation: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Read-only preflight

Run on the same host where the miner's stats endpoint is available:

```sh
python brain_v12/local_worker/bitcoin_worker_connection_check.py
```

The tool makes authenticated GET requests to Brain's worker status endpoint and the configured miner stats endpoint. It does not transmit a heartbeat. It prints no token or response body.

Expected success output includes:
- `BRAIN_API=reachable AUTH=accepted`
- `MINER_STATS_ENDPOINT=reachable REQUIRED_FIELDS=present`
- `RESULT=preflight_passed; no heartbeat sent and mining not verified`

A preflight failure should be fixed before starting the telemetry agent. A successful preflight only proves endpoint reachability and token acceptance; it does not prove a physical worker is hashing or that a pool accepted shares.

## Activation and evidence gates

1. Confirm Brain is deployed with the worker router mounted and HTTPS enabled.
2. Configure the same random token in Brain's secret environment and the authorized worker host.
3. Run the read-only preflight.
4. Start `bitcoin_worker_telemetry_agent.py` only on the authorized host with a genuine miner stats endpoint.
5. Verify fresh heartbeat timestamps in Brain status.
6. Verify accepted shares independently in the mining pool dashboard/API before claiming mining success.

The current API keeps the latest worker records in process memory. Persistence, independent pool-side evidence ingestion, and deployment-specific secret provisioning remain separate work. No credential or device access is created by committing these files.

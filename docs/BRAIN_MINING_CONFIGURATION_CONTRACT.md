# Brain Mining Configuration Contract

## Separate credential domains

Brain has two different authentication paths and they must not be conflated:

| Domain | Required environment variables | Purpose |
|---|---|---|
| Braiins read-only pool telemetry | `BRAIINS_POOL_API_TOKEN`, `BRAIINS_POOL_WORKER_ID` | Read pool-side worker telemetry using the pool token header |
| Brain worker telemetry intake | `BRAIN_MINING_WORKER_API_TOKEN` | Authenticate a worker's telemetry to Brain; minimum 32 characters |
| Worker connectivity | `BRAIN_MINING_API_URL`, `BRAIN_MINER_STATS_URL`, `BRAIN_MINING_WORKER_ID` | Identify Brain API, local stats endpoint, and worker identity |

The Braiins token is not the Brain worker API token. The worker API token is not
a Braiins pool token. Never copy one credential into the other variable to make
a readiness check pass.

## Read-only doctor

Run:

```bash
python brain_v12/tools/brain_mining_config_doctor.py
```

It reports only whether each variable is configured and whether limited format
policies pass. It never prints values, reads secret files, accesses the network,
starts a miner, or changes settings. It checks only the current process
environment; it does not automatically load `.brain_env` or another secret store.

## Evidence boundaries

- Configuration readiness is not proof that credentials are valid.
- Presence of a Braiins token does not prove its permissions are read-only.
- Worker self-reported telemetry does not prove accepted pool shares.
- This doctor never marks real mining, accepted shares, payouts, or revenue verified.

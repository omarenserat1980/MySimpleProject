# Brain ↔ Physical Bitcoin Worker API Channel

## Status

The authenticated worker telemetry router exists in `brain_v12/brain/bitcoin_worker_api.py` on branch `feat/brain-live-mining-worker-api-bridge`. It is **not yet mounted in `brain_v12/app.py`**, so these endpoints must not be treated as live until the router is imported and included by the application and verified from the running instance.

## Transport and authentication contract

- Serve only behind HTTPS; do not expose the worker endpoint on an unauthenticated public listener.
- Set `BRAIN_MINING_WORKER_API_TOKEN` in the runtime secret store/environment, never in source control. Use a random token of at least 32 characters and rotate it if exposed.
- The worker sends the token as a Bearer token. Never log or echo the token.
- The router accepts SHA-256d worker telemetry and enforces bounded numeric fields and a 120-second freshness window.
- Worker heartbeat data is self-reported. It is not proof of independently verified pool-accepted shares, real physical execution, or payout.

## Endpoints after router mounting

- `POST /api/bitcoin-mining/worker/heartbeat` — authenticated worker telemetry.
- `GET /api/bitcoin-mining/worker/status` — authenticated latest worker status.

## Connection acceptance gates

1. Mount `bitcoin_worker_api.router` in the actual Brain FastAPI application.
2. Verify the route appears in that running instance's OpenAPI document.
3. Verify requests without a token and with an invalid token are rejected.
4. Send a heartbeat from an explicitly authorized real worker over HTTPS.
5. Confirm the worker ID and heartbeat freshness in status.
6. Separately obtain pool-side accepted-share evidence before claiming live mining success. Do not equate a reported hashrate with accepted shares.
7. Keep simulation records and physical-worker evidence in separate fields and storage namespaces.

This channel is telemetry/control-plane plumbing only. It does not launch miners, issue remote shell commands, access wallet funds, or claim that a physical worker is connected.
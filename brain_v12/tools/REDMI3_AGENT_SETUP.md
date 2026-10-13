# Redmi3 / Termux Brain agent recovery

This runbook is deliberately conservative. It does not alter Android permissions, UID, sandbox settings, Render secrets, or queued tasks.

## 1. Configure the cloud credential

For the Termux-first setup, the default control plane is the Brain API on `http://127.0.0.1:8012`. Start Brain locally and verify `/health` and `/api/device/status` first. If you intentionally use a remote control plane, set `V12_BRAIN_URL` to its HTTPS base URL and configure **one** supported credential method on that existing service:

- Shared key: set `BRAIN_AGENT_KEY` to a strong random value, and set `BRAIN_ENABLE_DEVICE_BRIDGE=1`.
- Per-agent registry: set `BRAIN_AGENT_KEYS_JSON` to a JSON object mapping `redmi3-01` to its own strong random key, and set `BRAIN_ENABLE_DEVICE_BRIDGE=1`.

If `BRAIN_AGENT_KEYS_JSON` is present, it takes precedence over the shared-key method. Do not put a real key in GitHub, chat, logs, screenshots, or this runbook. Do not print it in a terminal. Keep the chosen key available for the Termux key file. Apply the credential configuration through the chosen control plane’s supported configuration path and wait until `/api/device/status` reports `configured=true` and `enabled=true`. Do not create or pay for a new cloud service for this workflow.

## 2. Prepare the existing Termux checkout

Run these commands **inside the Termux app on the Redmi3**, not through Remote Desktop Commander. The known Commander failure was `EACCES` when spawning Termux's shell; this runbook does not bypass that Android boundary.

From the repository checkout, update the checkout to a reviewed branch/commit containing these two scripts. The expected paths are:

- `brain_v12/tools/brain_device_preflight.py`
- `brain_v12/tools/termux_redmi3_launcher.sh`
- Existing worker: `brain_v12/tools/brain_emulator_agent.py`

Ensure the existing key is stored at `~/v12-agent/agent.key` (or set `V12_AGENT_KEY_FILE` to its actual path). The file must contain exactly the credential selected in step 1, with no surrounding quotes. Do not send the key to anyone.

## 3. Run preflight, then start the worker

From the repository root in Termux:

```sh
python brain_v12/tools/brain_device_preflight.py
```

This first command is read-only: it checks `/health` and `/api/device/status` and never prints a credential.

Only after the cloud reports `configured=true` and `enabled=true`, run:

```sh
sh brain_v12/tools/termux_redmi3_launcher.sh
```

The launcher sets the explicit Brain URL and `redmi3-01` identity, checks the key file, and sends one authenticated heartbeat. It starts the existing allowlisted worker loop only if preflight succeeds. It does not execute an arbitrary task itself. Keep the Termux session alive while testing.

## 4. Acceptance checks

1. `GET /api/device/status` shows `redmi3-01` online (the online TTL is short, currently 15 seconds).
2. The Termux process remains running and its output shows the explicit Brain URL and `Agent ID: redmi3-01`.
3. Only then enqueue a harmless `python_version` task through the approved Brain task interface and verify its returned report. Do not use the preflight script to poll the queue.
4. If authentication fails, stop. Compare the credential configuration without revealing either value; do not create a second Render service or weaken Android permissions.

## Important limitations

- A healthy HTTP service is not proof that the worker is running.
- One accepted heartbeat proves authentication and connectivity only; it does not prove task execution.
- These scripts have not been run on the physical Redmi3 by this repository change. Device acceptance requires the on-device steps above.

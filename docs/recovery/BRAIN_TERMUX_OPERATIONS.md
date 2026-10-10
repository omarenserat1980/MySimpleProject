# Brain Termux Operations

## Confirmed project path
/data/data/com.termux/files/home/MySimpleProject
Termux shorthand: ~/MySimpleProject

## Runtime scripts
- brain_v12/tools/brain_runtime_bootstrap.sh
- brain_v12/tools/brain_runtime_launcher.sh
- brain_v12/tools/brain_runtime_supervisor.py
- brain_v12/tools/brain_emulator_agent.py
- brain_v12/tools/brain_runtime_source_manager.sh

## Runtime state
~/MySimpleProject/.brain/state

Known operational files:
- api.log
- supervisor.log
- supervisor.pid
- continuous_supervisor.jsonl
- continuous_tasks.jsonl
- continuous_supervisor.lock
- runtime-bootstrap.log
- runtime-bootstrap.pid
- sync_queue.jsonl

## Agent configuration
File: ~/v12-agent/agent_config.sh

Confirmed non-secret values:
- V12_AGENT_ID=redmi3-01
- V12_AGENT_KEY_FILE=$HOME/v12-agent/agent.key
- V12_BRAIN_URL=http://127.0.0.1:8012

Secret material:
- ~/v12-agent/agent.key
- ~/.brain_env
Secret values are never documented or committed.

## Runtime contract
- API: 127.0.0.1:8012
- Uvicorn workers: 1
- Supervisor: single-instance lock
- Default supervisor interval: 60 seconds
- Minimum supervisor interval: 15 seconds

## Recovery rule
A replacement phone must obtain source/config from the canonical recovery path and must not depend on the old phone filesystem.

## Multi-device switching contract

### Device identity
- The launcher auto-maps only explicitly supported exact model identifiers: `23129RN51X` to `redmi3-01`, and `RMX3710` to `realme-01`.
- A model not in that exact allowlist must have a deliberately configured, unique `V12_AGENT_ID` and `V12_DEVICE_MODEL` equal to the exact `getprop ro.product.model` output in `~/v12-agent/agent_config.sh`. This pin is required to stop startup when an unknown phone inherits another device's config. Do not copy another phone's ID or model pin.
- If a recognized model conflicts with the configured ID, startup stops with `DEVICE_ID_MISMATCH`; investigate the model and local configuration instead of bypassing the guard.
- Brand names are not sufficient evidence of hardware identity. Update the allowlist only with verified model identifiers and corresponding tests.

### Endpoint and credential isolation
- `http://127.0.0.1:8012` is a loopback endpoint and refers only to the phone on which it is running. It is valid for a device hosting its own local Brain API, not as a way for another phone to reach Redmi.
- A non-primary agent must use an already reachable, authenticated Brain endpoint. If that endpoint is missing or unreachable, stop and diagnose networking; do not silently launch or terminate a local API as a substitute.
- Keep each phone's local key file at `~/v12-agent/agent.key`; never copy key material between phones or place it in Git.
- The backend supports an optional `BRAIN_AGENT_KEYS_JSON` registry mapping each agent ID to a unique key. When configured, it overrides legacy shared-key authentication and fails closed for missing IDs, invalid JSON, or duplicate key values. Configure it only in a local secret store such as `~/.brain_env`; never commit it or paste key values into chat.
- Each device's local `~/v12-agent/agent.key` must match the registry entry for that device ID on the Brain host. Transfer key material only through a secure channel you control. Do not copy the Redmi key to Realme or share one key across IDs.
- If the registry is not configured, legacy server-wide key mode remains active for compatibility. In that mode, a per-device key generated locally will not authenticate remotely unless it matches the server's configured key. Do not interpret local key creation as remote authorization.

### Evidence and release gates
- CI success proves only the checks that actually ran. It does not prove that a physical phone is connected or that a mission completed.
- Report source/CI validation, device reachability, authenticated heartbeat, mission execution, and recovery as separate evidence levels.
- Before enabling a second phone, record its exact model, configured ID, reachable Brain URL (without secrets), and authenticated heartbeat result.
- Never run destructive cleanup or overwrite local recovery state to make device switching pass. Preserve existing state and capture diagnostics first.

### Safe read-only preflight
On the target phone in Termux, inspect the model and architecture with `getprop ro.product.model` and `uname -m`; inspect the configured non-secret values in `~/v12-agent/agent_config.sh` without printing key files or `.brain_env`. Confirm the API endpoint is reachable before starting the agent. If any identity or endpoint value is uncertain, stop and correct configuration before launch.


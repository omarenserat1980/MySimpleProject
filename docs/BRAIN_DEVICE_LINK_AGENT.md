# Electronic Brain Device Link Agent

This tool lets an owner-operated Windows computer or Android Termux device establish an outbound, authenticated connection to Electronic Brain and report measured capacity. It uses HTTPS and the existing `POST /api/device/heartbeat` endpoint. It is heartbeat-only: it does not poll or claim queued tasks.

## Security boundary

- Observation-only: reports CPU count, total RAM when measurable, free disk, platform, and device model. Authenticated heartbeats include `enrolled=true`, which is required by the Android capacity adapter.
- Polls Brain for a strict allowlist of read-only tasks (`status`, `python_version`, `platform`). It rejects every other task; it never runs shell commands, interprets task parameters as code, reads arbitrary files, or uploads personal files.
- Never put a real key in Git, chat, screenshots, or shell history.
- The server must already have the agent ID/key enrolled in `BRAIN_AGENT_KEYS_JSON` (or an existing supported auth mode). A made-up key will correctly receive HTTP 401.
- Use a unique key per device. Revoke it from the server registry to disconnect that device.
- The service must be reachable over HTTPS; same Wi-Fi is not required for this outbound connection.

## Windows (Arkan)

Run in Windows PowerShell, not the Ubuntu `brain@arkan:~$` shell:

```powershell
$env:BRAIN_URL = "https://brain-control-plane-main.onrender.com"
$env:BRAIN_AGENT_ID = "windows-executor-arkan"
$env:BRAIN_AGENT_KEY = "<paste the already-enrolled key locally>"
python .\brain_v12\tools\brain_device_link.py --once
```

After a successful one-shot check, remove `--once` to keep sending heartbeats every 10 seconds. This agent does not claim tasks; task execution must use a separately authorized executor adapter. Keep the key in a local environment variable or protected secret store; do not commit it.

## Android (Realme / Redmi) in Termux

Install Python using Termux's package manager if it is not already installed, then copy the script to the phone (or clone the repository):

```sh
pkg install python
export BRAIN_URL="https://brain-control-plane-main.onrender.com"
export BRAIN_AGENT_ID="android-executor-realme"
export BRAIN_AGENT_KEY="<paste the already-enrolled key locally>"
python ~/MySimpleProject/brain_v12/tools/brain_device_link.py --once
```

Use `android-executor-redmi3-01` for the Redmi device if that is its enrolled ID. The ID must exactly match the server's key registry. Keep the process running without `--once` for ongoing heartbeats. This agent does not claim tasks.

## Expected evidence

A successful heartbeat prints JSON with `"ok": true`, `"http_status": 200`, and `"status": "HEARTBEAT"`. HTTP 401 means the key/ID is not enrolled or the device bridge is disabled. Network timeouts mean the device cannot currently reach the endpoint.

A successful heartbeat proves the agent can reach Brain and report measured capacity; it does not prove task execution or arbitrary remote shell access. Pool status becomes useful once the device-cloud-pool code is deployed and the device's recent heartbeat is present.

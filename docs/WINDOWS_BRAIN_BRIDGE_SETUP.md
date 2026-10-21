# Windows Brain Bridge — safe first connection

This guide applies to `tools/windows_brain_bridge_agent.py`. The bridge is opt-in,
outbound-only, and supports only the fixed read-only tasks `status`, `platform`,
and `python_version`. It does not provide a remote shell, reserve host resources,
or prove that a task was executed until Brain records a matching report.

## Before starting

1. Identify the **existing** Brain API endpoint and confirm it is reachable from this
   Windows computer. Use an HTTPS base URL with no path, query, fragment, or embedded
   credentials.
2. Register/configure the agent identity `windows-bridge-01` on that Brain instance
   using its supported device-bridge configuration. The server must accept the
   `X-V12-Agent-Id` and `X-V12-Agent-Key` headers and the existing heartbeat,
   poll, and report routes.
3. Obtain the already-authorized per-agent key through your existing secret-management
   process. Do not paste it into chat, GitHub, source files, command arguments, or logs.
   Do not generate a replacement key unless you also deliberately configure that new
   value on the server.
4. Do not assume `127.0.0.1` reaches another device. On Windows, it means this Windows
   computer. If Brain runs on a phone, use a reachable, approved HTTPS endpoint instead.

## Configure in PowerShell

Set the endpoint and exact hostname allowlist in the current PowerShell session. Replace
the example host with the real hostname approved for your Brain instance.

```powershell
$env:V12_AGENT_ID = "windows-bridge-01"
$env:V12_BRAIN_URL = "https://brain.example.invalid"
$env:V12_BRAIN_ALLOWED_HOSTS = "brain.example.invalid"
$env:V12_AGENT_KEY_FILE = "$HOME\.brain\agent.key"
```

Create the parent directory and store the **existing matching key** locally using your
approved secret-management method. Restrict access to the key file to the Windows account
that runs the agent. Never print the key to verify it.

## Run a local safety check

From a reviewed checkout of this repository:

```powershell
python -m unittest -v tests.test_windows_brain_bridge_agent
```

Then start the bridge explicitly:

```powershell
python tools/windows_brain_bridge_agent.py
```

Stop it with `Ctrl+C`. The agent sends an outbound heartbeat, polls the task endpoint,
and reports only fixed read-only task results. It refuses redirects and fails closed on
invalid configuration or malformed task payloads.

## Acceptance evidence

Do not mark the Windows host connected merely because the process starts or CI passes.
A real connection requires all of the following from the actual Brain instance:

- A recent authenticated heartbeat for `windows-bridge-01`.
- A successful poll response from the configured endpoint.
- A harmless allowlisted task such as `python_version` queued through the approved
  task interface.
- A server-side report matching the same agent and task ID, with timestamps or trace IDs
  that can be inspected without exposing credentials.

Record endpoint identity (hostname only), agent ID, UTC timestamps, HTTP outcome classes,
task ID, and report status. Redact authorization material. Keep `OBSERVED_HOST` and
`resource_reservation=NONE`; host telemetry is not a reservation and is not shared RAM.

If the service is unavailable, authentication is rejected, or the server-side route
contract is not confirmed, stop and diagnose the existing deployment. Do not disable
HTTPS, widen the hostname allowlist, expose an inbound port, or invent a successful result.

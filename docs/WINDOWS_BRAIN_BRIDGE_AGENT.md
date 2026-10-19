# Windows Bridge Agent (opt-in)

This agent is an outbound-only, user-mode adapter between Windows and the existing
Electronic Brain device-task API. It does not open a listener, execute shell or
PowerShell commands, install software, reserve memory, or provision cloud services.

## Requirements

- Python 3.10+ on the Windows host.
- An already running Brain API reachable from the host.
- A dedicated agent credential accepted by that Brain API. Never copy the phone's
  private key to Windows and never store credentials in Git.
- Prefer an HTTPS Brain URL. URL user-info, query strings, and fragments are rejected.\n- Optionally set `V12_BRAIN_ALLOWED_HOSTS` to a comma-separated exact hostname allowlist; when set, the configured endpoint host must match.\n- HTTP is rejected unless
  `BRAIN_ALLOW_INSECURE_HTTP=1` is explicitly set for a trusted test network;
  do not use that override on public or untrusted networks.

## Configure in the current PowerShell session

```powershell
$env:V12_BRAIN_URL = "https://YOUR-APPROVED-BRAIN-ENDPOINT"
$env:V12_AGENT_ID = "windows-bridge-01"
$env:V12_AGENT_KEY_FILE = "$HOME\.brain\agent.key"
python .\tools\windows_brain_bridge_agent.py
```

Create the key file locally using the control plane's approved enrollment process.
This agent intentionally does not generate, display, or distribute production keys.
Do not create the file by copying another device's key.

## Scope and evidence

Only `status`, `platform`, and `python_version` tasks are accepted. The status
task returns a bounded host-resource snapshot with `reality=OBSERVED_HOST` and
`resource_reservation=NONE`; telemetry does not mean those resources are
automatically added to another device's RAM.

A successful heartbeat proves that the API accepted a credential for an agent ID,
not unique hardware identity or attestation. End-to-end integration is verified
only after a task is queued, received, executed, reported, and checked in Brain.

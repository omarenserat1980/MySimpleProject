# Electronic Brain — Arkan Windows Heartbeat Agent

## Phase 1 scope

This agent creates an independent outbound connection from Arkan to the Brain API. It sends limited OS/Python/CPU/memory metadata and retries failures with exponential backoff. A native Windows Scheduled Task runs it as SYSTEM so it can survive logoff and reboot.

**It does not poll or execute tasks, change Hyper-V settings, start VMs, or install software by itself.** Desktop Commander remains a secondary channel. A heartbeat alone does not prove hardware identity, GitHub Runner health, Hyper-V readiness, or Windows Server 2025 boot.

## Prerequisites

- Python 3 installed on Arkan.
- Brain API reachable from Arkan.
- HTTPS for remote APIs; HTTP is allowed only for loopback development.
- Existing Brain agent key supplied through a trusted channel. Never commit it or send it in chat.
- PowerShell run as Administrator.

The current Brain API uses X-V12-Agent-Key and X-V12-Agent-Id on POST /api/device/heartbeat. This is the existing shared agent-auth mechanism, not unique device identity. Keep this agent heartbeat-only; do not infer remote task authorization from its heartbeat.

## Install on Arkan

From the repository root in an elevated PowerShell session:

§§§powershell
Set-ExecutionPolicy -Scope Process Bypass
.\brain_windows_agent\install_arkan_agent.ps1 -BrainUrl "https://YOUR-TRUSTED-BRAIN-API"
§§§

Replace the placeholder with the actual trusted HTTPS API URL. If the protected key file does not exist, the installer prompts for the existing Brain agent key with hidden input and writes it to C:\ProgramData\Brain\secrets\agent.key, ACL-restricted to SYSTEM and local Administrators. Do not use a general control-plane key if a dedicated agent key can be configured.

For local-only testing, http://127.0.0.1:8012 is accepted, but it only works if the API is running on the same Windows host.

## Verify connection

§§§powershell
Get-ScheduledTask -TaskName "ElectronicBrain-Arkan-Heartbeat" | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName "ElectronicBrain-Arkan-Heartbeat" | Select-Object LastRunTime, LastTaskResult, NumberOfMissedRuns
§§§

Then query the authenticated Brain device status endpoint and confirm arkan-windows-agent-01 has a recent heartbeat. A running task plus a fresh heartbeat is stronger evidence than task registration alone.

## Next gates

1. Prove a fresh heartbeat after network interruption and reboot.
2. Repair/register the GitHub Actions Runner separately and confirm it is Online with the brain-internal label.
3. Run the existing read-only Hyper-V preflight workflow.
4. Only after review and explicit authorization, consider any task-execution channel.
5. Verify Windows Server 2025 boot and remote accessibility independently.

No paid infrastructure is required by this agent.

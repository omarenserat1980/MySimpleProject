# Arkan Living AI Desktop

A lightweight Windows PowerShell/WPF desktop companion for Electronic Brain. It creates a movable, translucent always-on-top control panel and reads host telemetry plus the existing local Brain readiness endpoint.

## Run

On the ASUS Arkan Windows device, from a PowerShell window in the repository:

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\windows\arkan_living_ai_desktop.ps1

Optional Brain URL override:

$env:V12_BRAIN_URL = "http://127.0.0.1:8012"
.\tools\windows\arkan_living_ai_desktop.ps1

The app polls /api/system/readiness every five seconds. A successful response only proves the readiness endpoint responded; it does not prove a model is actively reasoning or that remote devices are connected. An unreachable endpoint is displayed as OFFLINE. CPU, memory, OS and hostname are read from the local Windows host.

## Safety and scope

- No admin rights required by design.
- No commands are run on behalf of Brain; buttons only refresh status, open the readiness URL, or change local presentation mode.
- No credentials are stored and no remote listener is opened.
- No automatic startup registration is created. Enable that separately only after reviewing the behavior.
- The panel is a first implementation, not a replacement for Windows Explorer or a complete shell.
- The current WPF panel uses native Windows APIs and may require Windows PowerShell 5.1 with .NET/WPF available.

## Verification status

Repository-side syntax checks can validate parsing, but they cannot prove the app launches on the physical Arkan machine. Physical launch, real Brain response, and resource use must be confirmed on Arkan itself.

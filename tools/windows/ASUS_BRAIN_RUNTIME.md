# ASUS VivoBook local Brain runtime

This procedure targets the ASUS VivoBook Windows computer. It does not create a VM,
enable Hyper-V, configure an auto-start service, open public ports, or provision cloud
resources.

## Prerequisites
- The repository is checked out on `feat/brain-free-cloud-capacity-gate`.
- The working tree is clean.
- Python 3.11+ and Git are installed.
- At least 2 GB of free disk space and 768 MB of currently free RAM are available.
- The machine owner is logged into Windows.

## Stage 1: read-only preflight

From PowerShell in the repository, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\tools\windows\asus_brain_runtime.ps1
```

This reports repository identity, branch, Python version, and available memory/disk.
It does not install packages or start Brain.

## Stage 2: isolated local activation

After reviewing the preflight report, run:

```powershell
.\tools\windows\asus_brain_runtime.ps1 -Activate
```

The script creates an isolated Python environment under the current user's
`%LOCALAPPDATA%\ElectronicBrain\venv-cloud-foundation`, installs the repository's
root requirements and pytest, compiles the cloud foundation modules, runs their
unit/integration tests, runs the repository's application preflight, and then starts
Uvicorn bound only to `127.0.0.1:8012`.

The runtime database and logs are stored under
`%LOCALAPPDATA%\ElectronicBrain\ASUS`. It disables live income search and workforce
execution for this activation attempt. If health/readiness checks fail, the process
started by this script is stopped and the script exits with an error.

## Success criteria

A successful script run must print:
- `BRAIN_ASUS_RUNTIME=RUNNING`
- `HEALTH=PASS`
- `READINESS=PASS`

The script's local startup check is not proof that any cloud task was executed.
The cloud executor deliberately remains review-only and reports
`PREPARED_NOT_EXECUTED`; real cloud execution requires a separately reviewed executor,
real provider evidence, explicit permissions, and another end-to-end test.

## Safety
- No cloud provider login is performed by this script.
- No paid cloud service is activated.
- No Windows service, scheduled task, or boot persistence is created.
- The server listens on loopback only.
- Existing processes are never killed when the requested port is occupied.
- A dirty worktree or unexpected branch causes the script to stop before activation.

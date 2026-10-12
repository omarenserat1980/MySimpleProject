[CmdletBinding()]
param(
    [string]$Workspace = (Get-Location).Path,
    [int]$Cycles = 0,
    [int]$PauseSeconds = 300
)

$ErrorActionPreference = "Stop"
Set-Location $Workspace

$env:CL3_EVOLUTION_PAUSE_SECONDS = [string]$PauseSeconds
$env:PYTHON = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }

Write-Host "CL-000003 / Arkan Evolution Guardian"
Write-Host "Workspace: $Workspace"
Write-Host "Mode: $(if ($Cycles -eq 0) { 'CONTINUOUS' } else { "BOUNDED ($Cycles cycles)" })"

& $env:PYTHON -m brain_v12.business.cl_000003_arkan_evolution --cycles $Cycles --pause $PauseSeconds
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host "CL3 ARKAN GUARDIAN: VERIFIED"
} else {
    Write-Error "CL3 ARKAN GUARDIAN: FAILED - inspect .brain/state/cl_000003_current_failure.json"
}

exit $code

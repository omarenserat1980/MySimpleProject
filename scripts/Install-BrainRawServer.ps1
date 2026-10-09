# Brain Raw Server Composer bootstrap for Windows Server 2025.
# Run from a checked-out repository root, or download this script from the project first.
[CmdletBinding()]
param(
    [string]$OutputPath = "$env:ProgramData\ElectronicBrain\RawServer\build",
    [double]$TargetRamGB = 0
)
$ErrorActionPreference = "Stop"
$Composer = Join-Path $PSScriptRoot "..\brain_v12\raw_server\composer.py"
$Composer = [System.IO.Path]::GetFullPath($Composer)
if (-not (Test-Path -LiteralPath $Composer -PathType Leaf)) {
    throw "Composer not found at '$Composer'. Run this script from a complete repository checkout."
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $Python) { throw "Python 3.11+ is required. Install Python from python.org or Windows Package Manager, then rerun." }
$PythonExe = $Python.Source
$Version = & $PythonExe --version 2>&1
if ($LASTEXITCODE -ne 0) { throw "Python could not be started." }
Write-Host "Python: $Version"
New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null
$Arguments = @($Composer, "--output", $OutputPath)
if ($TargetRamGB -gt 0) { $Arguments += @("--target-ram-gb", [string]$TargetRamGB) }
& $PythonExe @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "Brain Raw Server Composer did not pass every stage. Review '$OutputPath\evidence'. No VM or cloud resources were created."
}
Write-Host "Build plan created at: $OutputPath"
Write-Host "This is a software-defined capacity plan, not a running server or actual RAM allocation."

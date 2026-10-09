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
    # Bootstrap from a reviewed immutable commit, never from a mutable branch name.
    $Composer = Join-Path $env:ProgramData "ElectronicBrain\RawServer\composer.py"
    $ComposerDirectory = Split-Path -Parent $Composer
    New-Item -ItemType Directory -Force -Path $ComposerDirectory | Out-Null
    $PinnedCommit = "1f48c790e55b3d8df3279bda8e7078923316769e"
    $SourceUrl = "https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/$PinnedCommit/brain_v12/raw_server/composer.py"
    $TemporaryDownload = "$Composer.download-$PID"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        # Always refresh the fallback copy from the immutable source. Do not trust
        # a stale or locally modified ProgramData copy merely because it exists.
        Invoke-WebRequest -Uri $SourceUrl -OutFile $TemporaryDownload -UseBasicParsing -TimeoutSec 30
        if (-not (Test-Path -LiteralPath $TemporaryDownload -PathType Leaf) -or (Get-Item -LiteralPath $TemporaryDownload).Length -lt 1000) {
            throw "Downloaded composer file is missing or unexpectedly small."
        }
        Move-Item -LiteralPath $TemporaryDownload -Destination $Composer -Force
    }
    catch {
        Remove-Item -LiteralPath $TemporaryDownload -Force -ErrorAction SilentlyContinue
        throw "Could not download the pinned Brain Raw Server Composer. Check network access and retry. Details: $($_.Exception.Message)"
    }
}
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $Python) { throw "Python 3.11+ is required. Install Python from python.org or Windows Package Manager, then rerun." }
$PythonExe = $Python.Source
$Version = & $PythonExe --version 2>&1
if ($LASTEXITCODE -ne 0) { throw "Python could not be started." }
& $PythonExe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or newer is required. Detected: $Version" }
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

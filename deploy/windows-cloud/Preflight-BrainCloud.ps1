[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [string]$HealthUrl = "http://127.0.0.1:8012/api/system/readiness"
)

$ErrorActionPreference = "Stop"

Write-Host "Electronic Brain Windows Cloud preflight"
Write-Host "Repository: $RepoPath"
Write-Host "Health URL: $HealthUrl"

if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
    throw "Repository path does not exist. Clone/check out the approved revision first."
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
    throw "Python was not found. Install a supported Python 3 release before continuing."
}

$requirements = Join-Path $RepoPath "requirements.txt"
if (-not (Test-Path -LiteralPath $requirements)) {
    throw "requirements.txt was not found at repository root; inspect the project's dependency layout before installing."
}

$venvPython = Join-Path $RepoPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $python.Source -m venv (Join-Path $RepoPath ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }

& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

Push-Location $RepoPath
try {
    & $venvPython -c "import brain_v12.app; print('Brain import OK')"
    if ($LASTEXITCODE -ne 0) { throw "Brain import smoke test failed." }
}
finally {
    Pop-Location
}

try {
    $response = Invoke-WebRequest -Uri $HealthUrl -TimeoutSec 8 -UseBasicParsing
    Write-Host ("Health endpoint HTTP status: " + [int]$response.StatusCode)
    Write-Host $response.Content
}
catch {
    Write-Warning "Health endpoint is not reachable yet. Start the Brain runtime and rerun preflight; this is not a successful launch."
    Write-Warning $_.Exception.Message
    exit 2
}

Write-Host "Preflight complete. This script does not provision a VM or install a Windows service."

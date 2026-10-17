[CmdletBinding()]
param(
    [switch]$Activate,
    [int]$Port = 8012,
    [int]$StartupTimeoutSeconds = 45
)

$ErrorActionPreference = "Stop"
$ExpectedBranch = "feat/brain-free-cloud-capacity-gate"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$StateRoot = Join-Path $env:LOCALAPPDATA "ElectronicBrain\ASUS"
$VenvRoot = Join-Path $env:LOCALAPPDATA "ElectronicBrain\venv-cloud-foundation"
$LogOut = Join-Path $StateRoot "uvicorn.stdout.log"
$LogErr = Join-Path $StateRoot "uvicorn.stderr.log"
$PidFile = Join-Path $StateRoot "uvicorn.pid"
$StartedProcess = $null

function Stop-StartedProcess {
    if ($script:StartedProcess -and -not $script:StartedProcess.HasExited) {
        Stop-Process -Id $script:StartedProcess.Id -Force -ErrorAction SilentlyContinue
    }
}

function Assert-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "REQUIRED_COMMAND_MISSING:$Name"
    }
}

function Invoke-JsonEndpoint([string]$Uri) {
    return Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec 3
}

try {
    New-Item -ItemType Directory -Force -Path $StateRoot | Out-Null
    Set-Location $RepoRoot

    Assert-Command "git"
    Assert-Command "python"

    $branch = (git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0) { throw "GIT_BRANCH_CHECK_FAILED" }
    if ($branch -ne $ExpectedBranch) {
        throw "WRONG_BRANCH: expected '$ExpectedBranch', found '$branch'. Do not deploy an unverified branch."
    }

    $dirty = git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw "GIT_STATUS_CHECK_FAILED" }
    if ($dirty) {
        throw "WORKTREE_NOT_CLEAN: commit or safely stash local changes before activation."
    }

    $pythonVersion = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
    if ($LASTEXITCODE -ne 0) { throw "PYTHON_VERSION_CHECK_FAILED" }
    $versionParts = $pythonVersion.Split(".")
    if ([int]$versionParts[0] -lt 3 -or ([int]$versionParts[0] -eq 3 -and [int]$versionParts[1] -lt 11)) {
        throw "PYTHON_TOO_OLD: Python 3.11 or newer is required; found $pythonVersion"
    }

    $osInfo = Get-CimInstance Win32_OperatingSystem
    $freeMemoryMb = [math]::Round($osInfo.FreePhysicalMemory / 1024)
    $drive = [System.IO.Path]::GetPathRoot($RepoRoot)
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($drive.TrimEnd('\'))'"
    $freeDiskGb = if ($disk) { [math]::Round($disk.FreeSpace / 1GB, 2) } else { 0 }

    Write-Output "BRAIN_ASUS_PREFLIGHT=PASS"
    Write-Output "REPOSITORY=$RepoRoot"
    Write-Output "BRANCH=$branch"
    Write-Output "PYTHON=$pythonVersion"
    Write-Output "FREE_MEMORY_MB=$freeMemoryMb"
    Write-Output "FREE_DISK_GB=$freeDiskGb"
    Write-Output "RUNTIME_URL=http://127.0.0.1:$Port"

    if ($freeDiskGb -lt 2) { throw "INSUFFICIENT_FREE_DISK: at least 2 GB is required for isolated dependencies." }
    if ($freeMemoryMb -lt 768) { throw "INSUFFICIENT_FREE_MEMORY: refusing to start Brain below 768 MB free memory." }

    if (-not $Activate) {
        Write-Output "PREFLIGHT_ONLY=1"
        Write-Output "NEXT_ACTION=Re-run this script with -Activate after reviewing the preflight report."
        exit 0
    }

    if (-not (Test-Path (Join-Path $RepoRoot "requirements.txt"))) {
        throw "ROOT_REQUIREMENTS_MISSING"
    }
    if (-not (Test-Path (Join-Path $RepoRoot "brain_v12\tools\ci_preflight.py"))) {
        throw "BRAIN_CI_PREFLIGHT_MISSING"
    }

    if (-not (Test-Path (Join-Path $VenvRoot "Scripts\python.exe"))) {
        & python -m venv $VenvRoot
        if ($LASTEXITCODE -ne 0) { throw "VENV_CREATE_FAILED" }
    }
    $venvPython = Join-Path $VenvRoot "Scripts\python.exe"

    & $venvPython -m pip install -r (Join-Path $RepoRoot "requirements.txt") pytest
    if ($LASTEXITCODE -ne 0) { throw "DEPENDENCY_INSTALL_FAILED" }

    $env:PYTHONPATH = $RepoRoot
    $env:BRAIN_DB = Join-Path $StateRoot "brain-asus-isolated.db"
    $env:BRAIN_LIVE_INCOME_SEARCH_ENABLED = "false"
    $env:BRAIN_WORKFORCE_ENABLED = "false"
    $env:BRAIN_V14_VERSION = "14.0"

    $componentFiles = @(
        "brain_v12\brain\cloud_capacity_gate.py",
        "brain_v12\brain\cloud_provider_adapter.py",
        "brain_v12\brain\resource_fabric.py",
        "brain_v12\brain\task_scheduler.py",
        "brain_v12\brain\cloud_executor.py",
        "brain_v12\brain\verification_recovery.py",
        "brain_v12\brain\task_envelope.py",
        "brain_v12\brain\resource_health.py",
        "brain_v12\brain\execution_evidence_bundle.py",
        "brain_v12\brain\execution_lease.py",
        "brain_v12\brain\cloud_foundation_coordinator.py"
    )
    foreach ($file in $componentFiles) {
        & $venvPython -m py_compile (Join-Path $RepoRoot $file)
        if ($LASTEXITCODE -ne 0) { throw "PY_COMPILE_FAILED:$file" }
    }

    $testFiles = @(
        "brain_v12\tests\test_cloud_capacity_gate.py",
        "brain_v12\tests\test_cloud_provider_adapter.py",
        "brain_v12\tests\test_task_scheduler.py",
        "brain_v12\tests\test_cloud_executor.py",
        "brain_v12\tests\test_verification_recovery.py",
        "brain_v12\tests\test_task_envelope.py",
        "brain_v12\tests\test_resource_health.py",
        "brain_v12\tests\test_execution_evidence_bundle.py",
        "brain_v12\tests\test_execution_lease.py",
        "brain_v12\tests\test_cloud_foundation_integration.py",
        "brain_v12\tests\test_cloud_foundation_coordinator.py"
    )
    $absoluteTestFiles = @($testFiles | ForEach-Object { Join-Path $RepoRoot $_ })
    & $venvPython -m pytest -q $absoluteTestFiles
    if ($LASTEXITCODE -ne 0) { throw "CLOUD_FOUNDATION_TESTS_FAILED" }

    & $venvPython (Join-Path $RepoRoot "brain_v12\tools\ci_preflight.py")
    if ($LASTEXITCODE -ne 0) { throw "BRAIN_APPLICATION_PREFLIGHT_FAILED" }

    $existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($existing) { throw "PORT_ALREADY_IN_USE:$Port. No existing process was stopped." }

    $processArgs = @("-m", "uvicorn", "brain_v12.app:app", "--host", "127.0.0.1", "--port", "$Port")
    $StartedProcess = Start-Process -FilePath $venvPython -ArgumentList $processArgs -WorkingDirectory $RepoRoot -RedirectStandardOutput $LogOut -RedirectStandardError $LogErr -PassThru
    Set-Content -Path $PidFile -Value $StartedProcess.Id -Encoding ascii

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $healthy = $false
    while ((Get-Date) -lt $deadline) {
        if ($StartedProcess.HasExited) { throw "UVICORN_EXITED:$($StartedProcess.ExitCode)" }
        try {
            $health = Invoke-JsonEndpoint "http://127.0.0.1:$Port/health"
            if ($health.ok -eq $true) {
                $readiness = Invoke-JsonEndpoint "http://127.0.0.1:$Port/api/system/readiness"
                if ($readiness.ok -eq $true) {
                    $healthy = $true
                    break
                }
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    if (-not $healthy) {
        throw "READINESS_FAILED: inspect $LogOut and $LogErr; process will be stopped."
    }

    Write-Output "BRAIN_ASUS_RUNTIME=RUNNING"
    Write-Output "PID=$($StartedProcess.Id)"
    Write-Output "HEALTH=PASS"
    Write-Output "READINESS=PASS"
    Write-Output "URL=http://127.0.0.1:$Port"
    Write-Output "LOG_STDOUT=$LogOut"
    Write-Output "LOG_STDERR=$LogErr"
    Write-Output "NOTE=Local-only listener; no paid cloud resources or Windows services were created."
}
catch {
    Stop-StartedProcess
    Write-Error $_
    exit 1
}

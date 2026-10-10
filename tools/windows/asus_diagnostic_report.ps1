# Read-only diagnostic report for ASUS VivoBook / Electronic Brain.
# This script does not install software, change settings, start/stop processes,
# access secrets, or contact any remote/cloud endpoint.
$ErrorActionPreference = 'SilentlyContinue'

function Get-FreeDiskGB([string]$Drive) {
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$Drive'"
    if ($null -eq $disk -or $null -eq $disk.FreeSpace) { return $null }
    return [math]::Round($disk.FreeSpace / 1GB, 2)
}

$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gitBranch = $null
$gitStatus = $null
$repoRoot = $null
$cursor = (Get-Location).Path

while ($cursor) {
    if (Test-Path (Join-Path $cursor '.git')) {
        $repoRoot = $cursor
        break
    }
    $parent = Split-Path $cursor -Parent
    if (-not $parent -or $parent -eq $cursor) { break }
    $cursor = $parent
}

if ($repoRoot -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $gitBranch = (& git -C $repoRoot branch --show-current 2>$null | Out-String).Trim()
    $gitStatus = (& git -C $repoRoot status --short 2>$null | Out-String).Trim()
}

$pythonVersion = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonVersion = (& python --version 2>&1 | Out-String).Trim()
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonVersion = (& py -3 --version 2>&1 | Out-String).Trim()
}

$apiStatus = 'NOT_CHECKED'
$apiDetail = 'Loopback API check timed out or was unavailable.'
try {
    $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8012/api/system/readiness' -TimeoutSec 3
    $apiStatus = 'RESPONDED'
    $apiDetail = $response
} catch {
    $apiStatus = 'UNAVAILABLE'
    $apiDetail = $_.Exception.Message
}

$report = [ordered]@{
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    diagnostic_mode = 'READ_ONLY'
    host = $env:COMPUTERNAME
    os_caption = $os.Caption
    os_version = $os.Version
    os_architecture = $os.OSArchitecture
    manufacturer = $cs.Manufacturer
    model = $cs.Model
    cpu_name = $cpu.Name
    logical_processors = $cs.NumberOfLogicalProcessors
    ram_total_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
    ram_free_gb = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    c_drive_free_gb = Get-FreeDiskGB 'C:'
    python_version = $pythonVersion
    repository_root = $repoRoot
    git_branch = $gitBranch
    git_status_short = $gitStatus
    brain_api_status = $apiStatus
    brain_api_readiness = $apiDetail
    safety = @{
        installed_software = $false
        settings_changed = $false
        processes_started_or_stopped = $false
        secrets_collected = $false
        cloud_resources_created = $false
    }
}

$json = $report | ConvertTo-Json -Depth 7
Write-Output '=== ELECTRONIC BRAIN ASUS DIAGNOSTIC (READ ONLY) ==='
Write-Output $json
Write-Output '=== END DIAGNOSTIC ==='

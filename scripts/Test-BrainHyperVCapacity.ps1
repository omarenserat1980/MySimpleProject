# Read-only capacity gate for a specific existing Hyper-V VM.
# Does not create, start, stop, or modify any VM.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VMName,

    [ValidateRange(0.25, 128)]
    [double]$HostReserveGB = 2.0,

    [ValidateRange(0, 32)]
    [double]$HyperVOverheadGB = 0.5,

    [string]$OutputDirectory = "$env:ProgramData\ElectronicBrain\RawServer\evidence"
)

$ErrorActionPreference = "Stop"
$startedAt = [DateTime]::UtcNow
$issues = New-Object System.Collections.Generic.List[string]
$decision = "BLOCKED"
$reportPath = $null
$hash = $null

try {
    $computer = Get-CimInstance -ClassName Win32_ComputerSystem
    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    $capturedAt = [DateTime]::UtcNow
    $totalBytes = [uint64]$computer.TotalPhysicalMemory
    $availableBytes = [uint64]$os.FreePhysicalMemory * 1KB
    $reserveBytes = [uint64]($HostReserveGB * 1GB)
    $overheadBytes = [uint64]($HyperVOverheadGB * 1GB)

    if ($totalBytes -le 0 -or $availableBytes -le 0 -or $availableBytes -gt $totalBytes) {
        $issues.Add("Physical memory telemetry is invalid or inconsistent.")
    }

    $getVm = Get-Command Get-VM -ErrorAction SilentlyContinue
    if (-not $getVm) {
        $issues.Add("Hyper-V Get-VM cmdlet is unavailable.")
    }

    $vm = $null
    if ($getVm) {
        try {
            $vm = Get-VM -Name $VMName -ErrorAction Stop
        } catch {
            $issues.Add("Target VM could not be read: $VMName")
        }
    }

    if ($vm) {
        $requestedBytes = [uint64]$vm.MemoryStartup
        $vmState = [string]$vm.State
        $vmId = [string]$vm.Id
    } else {
        $requestedBytes = $null
        $vmState = "UNKNOWN"
        $vmId = $null
    }

    $budgetBytes = [int64]$availableBytes - [int64]$reserveBytes - [int64]$overheadBytes
    if ($budgetBytes -lt 0) {
        $issues.Add("Available memory is below the configured host reserve plus Hyper-V overhead.")
    }
    if ($null -eq $requestedBytes -or $requestedBytes -le 0) {
        $issues.Add("Target VM startup memory is unknown or invalid.")
    }
    if ($vmState -eq "Running") {
        $issues.Add("Target VM is already Running; this report is a capacity observation only, not a start authorization.")
    }

    if ($issues.Count -eq 0 -and [int64]$requestedBytes -le $budgetBytes) {
        $decision = "ALLOW_REVIEW_ONLY"
    } elseif ($issues.Count -eq 0) {
        $issues.Add("Target VM startup memory exceeds the safe budget.")
    }

    $report = [ordered]@{
        schema_version = "1.0"
        stage_id = "B1_hyperv_capacity_gate"
        target_device = $env:COMPUTERNAME
        started_at = $startedAt.ToString("o")
        completed_at = [DateTime]::UtcNow.ToString("o")
        telemetry_captured_at = $capturedAt.ToString("o")
        status = if ($decision -eq "ALLOW_REVIEW_ONLY") { "PASS" } else { "BLOCKED" }
        decision = $decision
        preconditions = [ordered]@{
            read_only = $true
            vm_start_attempted = $false
            vm_mutation_attempted = $false
        }
        observed_result = [ordered]@{
            host_total_bytes = $totalBytes
            host_available_bytes = $availableBytes
            host_reserve_bytes = $reserveBytes
            hyperv_overhead_bytes = $overheadBytes
            safe_budget_bytes = $budgetBytes
            vm_name = $VMName
            vm_id = $vmId
            vm_state = $vmState
            vm_startup_memory_bytes = $requestedBytes
            request_fits_budget = if ($null -ne $requestedBytes) { [int64]$requestedBytes -le $budgetBytes } else { $false }
        }
        issues = @($issues)
        verification_method = "Fresh local CIM memory telemetry plus Get-VM configuration read"
        next_action = if ($decision -eq "ALLOW_REVIEW_ONLY") { "Review result and obtain explicit authorization before any VM start. This is not a start command." } else { "Do not start the VM. Resolve telemetry, VM inventory, or capacity blockers and rerun." }
    }

    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $reportPath = Join-Path $OutputDirectory "capacity-$($VMName -replace '[^A-Za-z0-9_.-]', '_')-$stamp.json"
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    $hash = (Get-FileHash -LiteralPath $reportPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$reportPath.sha256" -Value "$hash  $(Split-Path -Leaf $reportPath)" -Encoding ASCII

    [pscustomobject]@{
        status = $report.status
        decision = $decision
        report_path = $reportPath
        sha256 = $hash
        issue_count = $issues.Count
        vm_start_attempted = $false
    } | ConvertTo-Json -Depth 3

    if ($decision -ne "ALLOW_REVIEW_ONLY") { exit 2 }
    exit 0
} catch {
    $failure = [ordered]@{
        schema_version = "1.0"
        stage_id = "B1_hyperv_capacity_gate"
        target_device = $env:COMPUTERNAME
        started_at = $startedAt.ToString("o")
        completed_at = [DateTime]::UtcNow.ToString("o")
        status = "BLOCKED"
        decision = "BLOCKED"
        vm_start_attempted = $false
        error = "$($_.Exception.GetType().Name): $($_.Exception.Message)"
        next_action = "Inspect the error and rerun after resolving it; this script never starts or modifies a VM."
    }
    try {
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
        $path = Join-Path $OutputDirectory "capacity-failure-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')).json"
        $failure | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding UTF8
    } catch { }
    Write-Error ($failure | ConvertTo-Json -Depth 5)
    exit 2
}

# Read-only Hyper-V preflight for Electronic Brain Raw Server Factory.
# This script never creates, starts, stops, deletes, or modifies a VM.
[CmdletBinding()]
param(
    [string]$OutputDirectory = "$env:ProgramData\ElectronicBrain\RawServer\evidence"
)

$ErrorActionPreference = "Stop"
$startedAt = [DateTime]::UtcNow.ToString("o")
$issues = New-Object System.Collections.Generic.List[string]
$observations = [ordered]@{}

try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    $computer = Get-CimInstance -ClassName Win32_ComputerSystem
    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    $processors = @(Get-CimInstance -ClassName Win32_Processor)
    $drives = @(Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
        [pscustomobject]@{
            device_id = $_.DeviceID
            size_bytes = [uint64]$_.Size
            free_bytes = [uint64]$_.FreeSpace
        }
    })

    $observations.target_device = [ordered]@{
        hostname = $env:COMPUTERNAME
        domain = $computer.Domain
        manufacturer = $computer.Manufacturer
        model = $computer.Model
        current_user = $identity.Name
        is_administrator = $isAdmin
    }
    $observations.operating_system = [ordered]@{
        caption = $os.Caption
        version = $os.Version
        build_number = $os.BuildNumber
        last_boot_utc = $os.LastBootUpTime.ToUniversalTime().ToString("o")
    }
    $observations.memory = [ordered]@{
        total_bytes = [uint64]$computer.TotalPhysicalMemory
        available_bytes = [uint64]$os.FreePhysicalMemory * 1KB
        source = "Win32_ComputerSystem.TotalPhysicalMemory + Win32_OperatingSystem.FreePhysicalMemory"
        captured_at_utc = [DateTime]::UtcNow.ToString("o")
    }
    $observations.cpu = [ordered]@{
        physical_socket_count = $processors.Count
        logical_processor_count = [int]$computer.NumberOfLogicalProcessors
        cores = [int]$computer.NumberOfLogicalProcessors
        virtualization_firmware_enabled = [bool]($processors | Where-Object { $_.VirtualizationFirmwareEnabled -eq $true } | Select-Object -First 1)
    }
    $observations.storage = $drives

    $getVm = Get-Command Get-VM -ErrorAction SilentlyContinue
    $vmms = Get-Service -Name vmms -ErrorAction SilentlyContinue
    $observations.hyperv = [ordered]@{
        get_vm_cmdlet_available = [bool]$getVm
        vmms_service_found = [bool]$vmms
        vmms_status = if ($vmms) { [string]$vmms.Status } else { "NOT_FOUND" }
        vm_inventory = @()
        inventory_read_succeeded = $false
    }

    if (-not $getVm) {
        $issues.Add("Hyper-V PowerShell cmdlet Get-VM is unavailable.")
    } elseif (-not $isAdmin) {
        $issues.Add("Current process is not elevated; Hyper-V inventory may be inaccessible. No elevation was attempted.")
    } else {
        try {
            $vms = @(Get-VM | ForEach-Object {
                [pscustomobject]@{
                    name = $_.Name
                    id = [string]$_.Id
                    state = [string]$_.State
                    generation = [int]$_.Generation
                    memory_startup_bytes = [uint64]$_.MemoryStartup
                    processor_count = [int]$_.ProcessorCount
                    configuration_location = [string]$_.ConfigurationLocation
                    snapshot_file_location = [string]$_.SnapshotFileLocation
                }
            })
            $observations.hyperv.vm_inventory = $vms
            $observations.hyperv.inventory_read_succeeded = $true
        } catch {
            $issues.Add("Hyper-V inventory query failed: $($_.Exception.GetType().Name): $($_.Exception.Message)")
        }
    }

    if ([uint64]$observations.memory.available_bytes -gt [uint64]$observations.memory.total_bytes) {
        $issues.Add("Available physical memory exceeds total physical memory; telemetry is inconsistent.")
    }
    if ([uint64]$observations.memory.total_bytes -le 0 -or [uint64]$observations.memory.available_bytes -le 0) {
        $issues.Add("Physical memory telemetry is missing or invalid.")
    }

    $status = if ($issues.Count -eq 0) { "PASS" } else { "BLOCKED" }
    $report = [ordered]@{
        schema_version = "1.0"
        stage_id = "A2_hyperv_read_only_preflight"
        target_device = $env:COMPUTERNAME
        started_at = $startedAt
        completed_at = [DateTime]::UtcNow.ToString("o")
        command_or_action = "Read-only local Windows/Hyper-V inventory"
        status = $status
        preconditions = [ordered]@{
            local_target_only = $true
            mutation_performed = $false
            privilege_escalation_attempted = $false
        }
        observed_result = $observations
        issues = @($issues)
        verification_method = "Windows CIM telemetry and Get-VM inventory when available"
        next_action = if ($status -eq "PASS") { "Review capacity policy; this report does not authorize VM start or creation." } else { "Resolve the listed telemetry, privilege, or Hyper-V blockers and rerun the read-only preflight." }
    }

    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssZ")
    $reportPath = Join-Path $OutputDirectory "hyperv-preflight-$stamp.json"
    $json = $report | ConvertTo-Json -Depth 8
    Set-Content -LiteralPath $reportPath -Value $json -Encoding UTF8
    $hash = (Get-FileHash -LiteralPath $reportPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath "$reportPath.sha256" -Value "$hash  $(Split-Path -Leaf $reportPath)" -Encoding ASCII

    [pscustomobject]@{
        status = $status
        report_path = $reportPath
        sha256 = $hash
        issue_count = $issues.Count
        mutation_performed = $false
    } | ConvertTo-Json -Depth 3

    if ($status -ne "PASS") { exit 2 }
    exit 0
} catch {
    $failure = [ordered]@{
        schema_version = "1.0"
        stage_id = "A2_hyperv_read_only_preflight"
        target_device = $env:COMPUTERNAME
        started_at = $startedAt
        completed_at = [DateTime]::UtcNow.ToString("o")
        status = "BLOCKED"
        mutation_performed = $false
        error = "$($_.Exception.GetType().Name): $($_.Exception.Message)"
        next_action = "Inspect the error; no VM or cloud resources were changed by this script."
    }
    try {
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
        $path = Join-Path $OutputDirectory "hyperv-preflight-failure-$([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')).json"
        $failure | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding UTF8
    } catch { }
    Write-Error ($failure | ConvertTo-Json -Depth 5)
    exit 2
}

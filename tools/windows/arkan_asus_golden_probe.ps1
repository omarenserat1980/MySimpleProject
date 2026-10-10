[CmdletBinding()]
param(
    [string]$ExpectedVmName = 'Brain-WindowsServer2025',
    [string]$ExpectedVhdxPath = 'C:\Brain-VM\Brain-WindowsServer2025.vhdx',
    [string]$WindowsServerIsoPath = ''
)

# Golden Loop Stage 1: OBSERVE only. No install, configuration, VM start/stop,
# disk mutation, network call, service change, or secret collection is performed.
$ErrorActionPreference = 'SilentlyContinue'

function Get-FreeSpaceGB([string]$Drive) {
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$Drive'"
    if ($null -eq $disk -or $null -eq $disk.FreeSpace) { return $null }
    return [math]::Round(([double]$disk.FreeSpace / 1GB), 2)
}
function Test-PathStatus([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) { return 'NOT_SPECIFIED' }
    if (Test-Path -LiteralPath $Path -PathType Leaf) { return 'PRESENT' }
    return 'MISSING'
}
function Add-Check([System.Collections.Generic.List[object]]$List, [string]$Name, [string]$Status, [string]$Detail) {
    $List.Add([ordered]@{ name = $Name; status = $Status; detail = $Detail }) | Out-Null
}

$checks = [System.Collections.Generic.List[object]]::new()
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$bios = Get-CimInstance Win32_BIOS
$memoryTotalGB = if ($cs) { [math]::Round(([double]$cs.TotalPhysicalMemory / 1GB), 2) } else { $null }
$memoryFreeGB = if ($os) { [math]::Round(([double]$os.FreePhysicalMemory / 1MB), 2) } else { $null }
$diskCFreeGB = Get-FreeSpaceGB 'C:'
$diskDFreeGB = Get-FreeSpaceGB 'D:'

$virtFirmware = if ($null -ne $cpu.VirtualizationFirmwareEnabled) { [bool]$cpu.VirtualizationFirmwareEnabled } else { $null }
$slat = if ($null -ne $cpu.SecondLevelAddressTranslationExtensions) { [bool]$cpu.SecondLevelAddressTranslationExtensions } else { $null }
$hyperVModule = [bool](Get-Command Get-VM -ErrorAction SilentlyContinue)
$vmStatus = 'UNAVAILABLE'
$vmMemoryMB = $null
$vmGeneration = $null
$vmPath = $null
if ($hyperVModule) {
    $vm = Get-VM -Name $ExpectedVmName -ErrorAction SilentlyContinue
    if ($vm) {
        $vmStatus = [string]$vm.State
        $vmMemoryMB = [math]::Round(([double]$vm.MemoryAssigned / 1MB), 0)
        $vmGeneration = $vm.Generation
        $vmPath = $vm.Path
    } else {
        $vmStatus = 'NOT_FOUND'
    }
}
$vhdxStatus = Test-PathStatus $ExpectedVhdxPath
$isoStatus = Test-PathStatus $WindowsServerIsoPath
$apiStatus = 'UNAVAILABLE'
try {
    $api = Invoke-RestMethod -Uri 'http://127.0.0.1:8012/api/system/readiness' -TimeoutSec 2
    $apiStatus = 'RESPONDED'
} catch { }

if ($cs -and $os) { Add-Check $checks 'host_identity' 'OBSERVED' "$($env:COMPUTERNAME); $($cs.Manufacturer) $($cs.Model); $($os.Caption) $($os.Version)" }
else { Add-Check $checks 'host_identity' 'UNKNOWN' 'CIM data unavailable' }
if ($null -ne $memoryFreeGB) { Add-Check $checks 'memory_headroom' 'OBSERVED' "total_gb=$memoryTotalGB; free_gb=$memoryFreeGB; no threshold declared yet" }
else { Add-Check $checks 'memory_headroom' 'UNKNOWN' 'Memory data unavailable' }
if ($null -ne $diskCFreeGB) { Add-Check $checks 'system_disk' 'OBSERVED' "C_free_gb=$diskCFreeGB; D_free_gb=$diskDFreeGB" }
else { Add-Check $checks 'system_disk' 'UNKNOWN' 'System disk data unavailable' }
if ($null -ne $virtFirmware) { Add-Check $checks 'firmware_virtualization' $(if ($virtFirmware) { 'PASS' } else { 'FAIL' }) "VirtualizationFirmwareEnabled=$virtFirmware; SLAT=$slat" }
else { Add-Check $checks 'firmware_virtualization' 'UNKNOWN' 'Firmware virtualization property unavailable' }
Add-Check $checks 'hyperv_management' $(if ($hyperVModule) { 'AVAILABLE' } else { 'UNAVAILABLE' }) 'Read-only Get-VM command availability'
Add-Check $checks 'target_vm' $vmStatus "name=$ExpectedVmName; state=$vmStatus; generation=$vmGeneration; assigned_memory_mb=$vmMemoryMB; path=$vmPath"
Add-Check $checks 'target_vhdx' $vhdxStatus "path=$ExpectedVhdxPath"
Add-Check $checks 'windows_server_iso' $isoStatus "path=$WindowsServerIsoPath"
Add-Check $checks 'brain_loopback_api' $apiStatus 'Only 127.0.0.1:8012/api/system/readiness was checked; no remote endpoint contacted'

$payload = [ordered]@{
    schema = 'brain.arkan-asus-golden-loop-observation.v1'
    mission = 'ARKAN_ASUS_COMPUTER_BUILD'
    stage = 'OBSERVE'
    observed_at_utc = [DateTime]::UtcNow.ToString('o')
    host = @{
        computer_name = $env:COMPUTERNAME
        manufacturer = $cs.Manufacturer
        model = $cs.Model
        serial_number_collected = $false
        os_caption = $os.Caption
        os_version = $os.Version
        os_architecture = $os.OSArchitecture
        bios_version = ($bios.SMBIOSBIOSVersion -join '; ')
        cpu_name = $cpu.Name
        logical_processors = $cs.NumberOfLogicalProcessors
        memory_total_gb = $memoryTotalGB
        memory_free_gb = $memoryFreeGB
        system_drive_free_gb = $diskCFreeGB
        data_drive_free_gb = $diskDFreeGB
        virtualization_firmware_enabled = $virtFirmware
        slat_supported = $slat
    }
    hyperv = @{
        management_module_available = $hyperVModule
        target_vm_name = $ExpectedVmName
        target_vm_state = $vmStatus
        target_vm_generation = $vmGeneration
        target_vm_assigned_memory_mb = $vmMemoryMB
        target_vm_path = $vmPath
        target_vhdx_path = $ExpectedVhdxPath
        target_vhdx_status = $vhdxStatus
        windows_server_iso_path = $WindowsServerIsoPath
        windows_server_iso_status = $isoStatus
    }
    brain_api = @{ status = $apiStatus; endpoint = 'http://127.0.0.1:8012/api/system/readiness' }
    checks = @($checks)
    loop = @{
        next_stage = 'VERIFY_OBSERVATION_AND_PLAN'
        state = 'OPEN_NOT_CLOSED'
        execution_performed = $false
        acceptance_claimed = $false
        real_host_evidence = $true
        approval_required_before_vm_or_system_changes = $true
    }
    safety = @{
        software_installed = $false
        settings_changed = $false
        processes_started_or_stopped = $false
        vm_started_or_stopped = $false
        disks_modified = $false
        network_or_cloud_resources_created = $false
        secrets_or_serial_numbers_collected = $false
    }
}
# Hash the exact compact JSON string and include that exact string so a reviewer
# can independently recompute SHA-256 without guessing serializer whitespace.
$payloadJson = $payload | ConvertTo-Json -Depth 8 -Compress
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($payloadJson)
    $payloadHash = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
} finally { $sha.Dispose() }
$result = [ordered]@{
    payload_sha256 = $payloadHash
    payload_canonical_json = $payloadJson
    payload = $payload
}
Write-Output '=== BRAIN GOLDEN LOOP / ARKAN ASUS — READ-ONLY OBSERVATION ==='
$result | ConvertTo-Json -Depth 10
Write-Output '=== END OBSERVATION ==='

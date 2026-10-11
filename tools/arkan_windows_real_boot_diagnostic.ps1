# Electronic Brain — Arkan Windows real-boot diagnostic
# Read-only. Does not modify Hyper-V, VMs, disks, services, secrets, or runner configuration.
# Run in PowerShell on Arkan. Writes a sanitized JSON report to the current directory.
$ErrorActionPreference = 'Continue'
$report = [ordered]@{
  schema = 'brain.arkan.windows-real-boot-diagnostic.v1'
  generated_utc = [DateTime]::UtcNow.ToString('o')
  machine = $env:COMPUTERNAME
  checks = [ordered]@{}
  warnings = @()
}
function Add-Check([string]$Name, $Value) { $report.checks[$Name] = $Value }
function Safe-Command([string]$Name, [scriptblock]$Block) {
  try { return & $Block } catch { $report.warnings += "$Name : $($_.Exception.GetType().Name)"; return $null }
}

Add-Check 'os' (Safe-Command 'os' { Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture })
Add-Check 'hardware' (Safe-Command 'hardware' { Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, @{N='RAM_GiB';E={[math]::Round($_.TotalPhysicalMemory/1GB,2)}}, NumberOfLogicalProcessors })
Add-Check 'cpu_virtualization' (Safe-Command 'cpu_virtualization' { Get-CimInstance Win32_Processor | Select-Object Name, VirtualizationFirmwareEnabled, VMMonitorModeExtensions, SecondLevelAddressTranslationExtensions })
Add-Check 'hyperv_feature' (Safe-Command 'hyperv_feature' {
  if (Get-Command Get-WindowsOptionalFeature -ErrorAction SilentlyContinue) {
    Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All | Select-Object FeatureName, State
  } else { 'Get-WindowsOptionalFeature unavailable (possibly not Windows client)' }
})
Add-Check 'hyperv_commands' (Safe-Command 'hyperv_commands' {
  [ordered]@{
    GetVM = [bool](Get-Command Get-VM -ErrorAction SilentlyContinue)
    GetVMHost = [bool](Get-Command Get-VMHost -ErrorAction SilentlyContinue)
  }
})
Add-Check 'vms' (Safe-Command 'vms' {
  if (Get-Command Get-VM -ErrorAction SilentlyContinue) {
    @(Get-VM | Select-Object Name, State, Status, Generation, MemoryStartup, MemoryAssigned, Uptime)
  } else { @() }
})
Add-Check 'hyperv_host' (Safe-Command 'hyperv_host' {
  if (Get-Command Get-VMHost -ErrorAction SilentlyContinue) {
    Get-VMHost | Select-Object ComputerName, VirtualMachinePath, VirtualHardDiskPath, LogicalProcessorCount, MemoryCapacity
  } else { $null }
})
Add-Check 'runner_services' (Safe-Command 'runner_services' {
  @(Get-CimInstance Win32_Service | Where-Object {
    $_.Name -match 'actions\.runner' -or $_.DisplayName -match 'GitHub Actions Runner'
  } | Select-Object Name, State, StartMode, StartName)
})
Add-Check 'runner_directories' (Safe-Command 'runner_directories' {
  $roots = @('C:\actions-runner','C:\GitHub\actions-runner','C:\brain-runner','C:\Brain')
  @($roots | ForEach-Object {
    [ordered]@{ Path = $_; Exists = (Test-Path -LiteralPath $_) }
  })
})
Add-Check 'disk_space' (Safe-Command 'disk_space' {
  @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, @{N='Size_GiB';E={[math]::Round($_.Size/1GB,2)}}, @{N='Free_GiB';E={[math]::Round($_.FreeSpace/1GB,2)}})
})
Add-Check 'candidate_vm_files' (Safe-Command 'candidate_vm_files' {
  $paths = @('C:\Brain-VM\Brain-WindowsServer2025.vhdx', 'C:\Brain-VM\Brain-WindowsServer2025.iso')
  @($paths | ForEach-Object {
    if (Test-Path -LiteralPath $_) {
      $item = Get-Item -LiteralPath $_
      [ordered]@{ Path = $_; Exists = $true; LengthBytes = $item.Length; LastWriteTimeUtc = $item.LastWriteTimeUtc.ToString('o') }
    } else { [ordered]@{ Path = $_; Exists = $false } }
  })
})
Add-Check 'git' (Safe-Command 'git' {
  if (Get-Command git -ErrorAction SilentlyContinue) { git --version 2>&1 | Out-String } else { 'git unavailable' }
})

# Avoid collecting environment variables, tokens, credentials, full process command lines, or private keys.
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
$out = Join-Path (Get-Location) "brain-arkan-preflight-$stamp.json"
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $out -Encoding UTF8
Write-Output "REPORT_PATH=$out"
Write-Output "MACHINE=$($report.machine)"
Write-Output "CHECK_COUNT=$($report.checks.Count)"
Write-Output "WARNING_COUNT=$($report.warnings.Count)"
Write-Output 'READ_ONLY=true'
Write-Output 'WINDOWS_BOOT_VERIFIED=false'

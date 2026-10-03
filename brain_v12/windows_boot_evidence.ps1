$ErrorActionPreference = 'Continue'
$deadline = (Get-Date).AddMinutes(10)
$vol = $null
while ((Get-Date) -lt $deadline -and -not $vol) {
  $vol = Get-Volume | Where-Object { $_.FileSystemLabel -eq 'BRAIN_EVIDENCE' } | Select-Object -First 1
  if ($vol -and -not $vol.DriveLetter) {
    try {
      $part = Get-Partition | Where-Object { -not $_.DriveLetter -and $_.Size -gt 0 } | Select-Object -First 1
      if ($part) { $part | Set-Partition -NewDriveLetter 'B' -ErrorAction SilentlyContinue }
    } catch {}
    $vol = Get-Volume | Where-Object { $_.FileSystemLabel -eq 'BRAIN_EVIDENCE' -and $_.DriveLetter } | Select-Object -First 1
  }
  if (-not $vol) { Start-Sleep -Seconds 5 }
}
if (-not $vol) { exit 20 }
$root = "$($vol.DriveLetter):\"
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$osIsServer2025 = ($os.Caption -match 'Windows Server 2025')
$arch = if ($env:PROCESSOR_ARCHITECTURE -match 'AMD64') { 'AMD64' } else { $env:PROCESSOR_ARCHITECTURE }
$adapters = @(Get-NetAdapter | Where-Object Status -eq 'Up' | ForEach-Object { @{name=$_.Name; status=$_.Status; mac=$_.MacAddress; description=$_.InterfaceDescription} })
$ips = @(Get-NetIPConfiguration | ForEach-Object { $_.IPv4Address | ForEach-Object { @{interface=$_.InterfaceAlias; ip=$_.IPv4Address} } })
$networkReady = ($adapters.Count -gt 0 -and $ips.Count -gt 0)
$internet = $false
for ($i = 0; $i -lt 20 -and -not $internet; $i++) {
  try { $internet = (Test-NetConnection -ComputerName 1.1.1.1 -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue) } catch {}
  if (-not $internet) { Start-Sleep -Seconds 3 }
}
$systemDrive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'"
$bootTime = [System.Management.ManagementDateTimeConverter]::ToDateTime($os.LastBootUpTime)
$evidence = [ordered]@{
 schema='BRAIN-WINDOWS-BOOT-EVIDENCE-1'
 status=if ($osIsServer2025) { 'WINDOWS_BOOT_VERIFIED' } else { 'WINDOWS_BOOT_REJECTED_OS_MISMATCH' }
 collected_at=(Get-Date).ToUniversalTime().ToString('o')
 guest=[ordered]@{ os=if ($osIsServer2025) { 'Windows Server 2025' } else { $os.Caption }; os_caption=$os.Caption; architecture=$arch; version=$os.Version; build=$os.BuildNumber; boot_time=$bootTime.ToUniversalTime().ToString('o'); computer_name=$cs.Name; boot_verified=$true }
 network=[ordered]@{ adapter_up=$networkReady; internet_443=$internet; adapters=$adapters; addresses=$ips }
 storage=[ordered]@{ system_drive=$env:SystemDrive; filesystem=$systemDrive.FileSystem; size_bytes=[int64]$systemDrive.Size; free_bytes=[int64]$systemDrive.FreeSpace; evidence_volume=$vol.FileSystemLabel }
}
$evidence | ConvertTo-Json -Depth 8 | Set-Content -Path ($root+'windows-boot-evidence.json') -Encoding UTF8
'BRAIN_WINDOWS_EVIDENCE_WRITTEN' | Set-Content -Path ($root+'WINDOWS_BOOT_VERIFIED') -Encoding ASCII
if (-not $osIsServer2025) { exit 21 }
exit 0
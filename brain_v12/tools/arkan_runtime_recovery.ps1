param(
 [string]$VMName="Brain-WindowsServer2025",
 [string]$VhdPath="C:\Brain-VM\Brain-WindowsServer2025.vhdx",
 [string]$IsoPath="",
 [string]$EvidenceDir="$env:USERPROFILE\Brain-Recovery-Evidence",
 [switch]$StartVM
)
$ErrorActionPreference="Continue"
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
$report=Join-Path $EvidenceDir ("arkan-recovery-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".txt")
Start-Transcript -Path $report -Force | Out-Null
"=== HOST RESOURCES ==="
Get-CimInstance Win32_OperatingSystem | Select-Object CSName,Caption,Version,@{n="TotalRAM_GB";e={[math]::Round($_.TotalVisibleMemorySize/1MB,2)}},@{n="FreeRAM_GB";e={[math]::Round($_.FreePhysicalMemory/1MB,2)}} | Format-List
Get-Volume | Select-Object DriveLetter,FileSystemLabel,@{n="FreeGB";e={[math]::Round($_.SizeRemaining/1GB,2)}} | Format-Table -AutoSize
"=== HYPER-V SERVICE ==="
Get-Service vmms -ErrorAction SilentlyContinue | Select-Object Name,Status,StartType | Format-List
"=== VM INVENTORY ==="
if (Get-Command Get-VM -ErrorAction SilentlyContinue) {
 Get-VM | Select-Object Name,State,Status,Generation,@{n="StartupRAM_GB";e={[math]::Round($_.MemoryStartup/1GB,2)}} | Format-Table -AutoSize
 $vm=Get-VM -Name $VMName -ErrorAction SilentlyContinue
 if ($vm) { Get-VMHardDiskDrive -VM $vm | Select-Object VMName,Path | Format-Table -AutoSize; Get-VMDvdDrive -VM $vm -ErrorAction SilentlyContinue | Select-Object VMName,Path | Format-Table -AutoSize } else { "VM_NOT_FOUND: $VMName" }
} else { "HYPERV_CMDLETS_UNAVAILABLE" }
"=== ARTIFACT PATHS ==="
foreach($p in @($VhdPath,$IsoPath) | Where-Object {$_}) { [pscustomobject]@{Path=$p;Exists=(Test-Path -LiteralPath $p)} | Format-List }
"=== GITHUB RUNNER ==="
Get-Service -ErrorAction SilentlyContinue | Where-Object {$_.Name -like "actions.runner*"} | Select-Object Name,Status,StartType | Format-Table -AutoSize
Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -match "Runner.Listener|Runner.Worker"} | Select-Object ProcessName,Id | Format-Table -AutoSize
"=== RECENT HYPER-V EVENTS ==="
foreach($log in @("Microsoft-Windows-Hyper-V-VMMS-Admin","Microsoft-Windows-Hyper-V-Worker-Admin")) { Get-WinEvent -FilterHashtable @{LogName=$log;StartTime=(Get-Date).AddDays(-3)} -MaxEvents 30 -ErrorAction SilentlyContinue | Select-Object TimeCreated,Id,LevelDisplayName,Message | Format-List }
if (-not $StartVM) { "READ_ONLY_MODE: no VM started or modified." }
else {
 if (-not (Get-Command Get-VM -ErrorAction SilentlyContinue)) { throw "Hyper-V cmdlets unavailable" }
 $vm=Get-VM -Name $VMName -ErrorAction Stop
 if ($vm.State -eq "Running") { "VM_ALREADY_RUNNING" }
 else {
  $freeMB=[math]::Floor((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1024)
  $startupMB=[math]::Ceiling($vm.MemoryStartup/1MB)
  if ($freeMB -lt ($startupMB+768)) { "START_BLOCKED_LOW_MEMORY: free=$($freeMB)MB startup=$($startupMB)MB reserve=768MB" }
  else { Start-VM -Name $VMName -ErrorAction Stop | Out-String | Write-Output; Start-Sleep -Seconds 5; Get-VM -Name $VMName | Select-Object Name,State,Status | Format-List; "VM_POWER_STATE_RUNNING_ONLY: verify Windows boot and login in VM console." }
 }
}
"Evidence: $report"
Stop-Transcript | Out-Null
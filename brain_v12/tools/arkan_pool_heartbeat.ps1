# Electronic Brain — Arkan Windows capacity heartbeat (observation only)
# Configure these in this PowerShell session; never commit real secrets.
# $env:BRAIN_URL = "https://<your-control-plane-host>"
# $env:BRAIN_AGENT_ID = "windows-executor-arkan"
# $env:BRAIN_AGENT_KEY = "<the enrolled agent key>"
$ErrorActionPreference = "Stop"
if (-not $env:BRAIN_URL -or -not $env:BRAIN_AGENT_ID -or -not $env:BRAIN_AGENT_KEY) { throw "Set BRAIN_URL, BRAIN_AGENT_ID, and BRAIN_AGENT_KEY before running." }
if ($env:BRAIN_AGENT_ID -notlike "windows-executor-*") { throw "BRAIN_AGENT_ID must start with windows-executor-." }
function Get-FreeDiskMb { $drive = Get-PSDrive -Name ($env:SystemDrive.TrimEnd(':')) -ErrorAction Stop; return [int][math]::Floor($drive.Free / 1MB) }
while ($true) {
  $os = Get-CimInstance Win32_OperatingSystem
  $cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
  $memoryMb = [int][math]::Floor([double]$os.TotalVisibleMemorySize / 1024)
  $metadata = @{ platform = "windows"; hostname = $env:COMPUTERNAME; cpu_cores = [double]$cpu; memory_mb = $memoryMb; disk_mb = (Get-FreeDiskMb); healthy = $true; capabilities = @("device.status", "device.info", "python.test"); observation_only = $true }
  $body = @{ agent_id = $env:BRAIN_AGENT_ID; metadata = $metadata } | ConvertTo-Json -Depth 6
  $headers = @{ "X-V12-Agent-Key" = $env:BRAIN_AGENT_KEY; "X-V12-Agent-Id" = $env:BRAIN_AGENT_ID }
  Invoke-RestMethod -Method Post -Uri "$($env:BRAIN_URL.TrimEnd('/'))/api/device/heartbeat" -Headers $headers -ContentType "application/json" -Body $body | Out-Null
  Start-Sleep -Seconds 10
}

param(
  [string]$BrainFabricUrl = $env:BRAIN_FABRIC_URL,
  [string]$NodeId = $env:BRAIN_WINDOWS_NODE_ID,
  [string]$EnrollmentToken = $env:BRAIN_ENROLLMENT_TOKEN
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($BrainFabricUrl) -or
    [string]::IsNullOrWhiteSpace($NodeId) -or
    [string]::IsNullOrWhiteSpace($EnrollmentToken)) {
  Write-Error "BRAIN_FABRIC_URL, BRAIN_WINDOWS_NODE_ID and BRAIN_ENROLLMENT_TOKEN are required"
  exit 2
}

$machine = Get-CimInstance Win32_OperatingSystem
$arch = (Get-CimInstance Win32_Processor | Select-Object -First 1).AddressWidth
if ($machine.Caption -notmatch "Windows Server 2025") {
  Write-Error "WINDOWS_SERVER_2025_REQUIRED"
  exit 3
}
if ($arch -ne 64) {
  Write-Error "X86_64_REQUIRED"
  exit 4
}

$body = @{
  enrollment_token = $EnrollmentToken
  state = "READY"
  jobs_running = 0
  architecture = "x86_64"
  capabilities = @("windows-server-2025","windows-cloud","brain-task-execution","brain-heartbeat","brain-evidence")
} | ConvertTo-Json

$headers = @{ Authorization = "Bearer $EnrollmentToken"; "Content-Type" = "application/json" }
Invoke-RestMethod -Method Post -Uri "$($BrainFabricUrl.TrimEnd('/'))/v1/fabric/nodes/$NodeId/heartbeat" -Headers $headers -Body $body | ConvertTo-Json -Depth 8

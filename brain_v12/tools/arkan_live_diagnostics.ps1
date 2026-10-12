# Electronic Brain — Arkan live diagnostics
# Read-only host checks + bounded command inside Brain's virtual PowerShell emulator.
# No real-host command is sent through Brain's simulation API.
[CmdletBinding()]
param(
    [string]$BrainBaseUrl = $(if ($env:BRAIN_BASE_URL) { $env:BRAIN_BASE_URL } else { "http://127.0.0.1:8012" }),
    [string]$EvidenceDirectory = "C:\Brain\diagnostics"
)
$ErrorActionPreference = "Stop"
$BrainBaseUrl = $BrainBaseUrl.TrimEnd("/")
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$evidence = [ordered]@{
    schema = "electronic-brain.arkan-live-diagnostics.v1"
    checked_at = (Get-Date).ToString("o")
    host = [ordered]@{}
    api = [ordered]@{}
    simulation = [ordered]@{}
    notes = @()
}
try {
    $os = Get-CimInstance Win32_OperatingSystem
    $evidence.host = [ordered]@{
        computer_name = $env:COMPUTERNAME
        os_caption = $os.Caption
        os_version = $os.Version
        last_boot = $os.LastBootUpTime.ToString("o")
        powershell_version = $PSVersionTable.PSVersion.ToString()
    }
} catch {
    $evidence.notes += "HOST_OS_QUERY_FAILED: $($_.Exception.Message)"
}
try {
    $evidence.host.hyper_v = @(Get-VM -ErrorAction Stop | Select-Object Name, State, Status)
} catch {
    $evidence.host.hyper_v = @()
    $evidence.notes += "HYPER_V_QUERY_UNAVAILABLE: $($_.Exception.Message)"
}
try {
    $evidence.api.system_readiness = Invoke-RestMethod -Method Get -Uri "$BrainBaseUrl/api/system/readiness" -TimeoutSec 8
} catch {
    $evidence.api.system_readiness_error = $_.Exception.Message
}
try {
    $evidence.api.remote_fabric_before = Invoke-RestMethod -Method Get -Uri "$BrainBaseUrl/api/remote-fabric/status" -TimeoutSec 8
} catch {
    $evidence.api.remote_fabric_status_error = $_.Exception.Message
}
$key = [Environment]::GetEnvironmentVariable("BRAIN_CONTROL_KEY", "Process")
if (-not $key) { $key = [Environment]::GetEnvironmentVariable("BRAIN_CONTROL_KEY", "User") }
if (-not $key) { $key = [Environment]::GetEnvironmentVariable("BRAIN_CONTROL_KEY", "Machine") }
if ($key) {
    $headers = @{ "X-Brain-Control-Key" = $key }
    try {
        $connect = Invoke-RestMethod -Method Post -Uri "$BrainBaseUrl/api/remote-fabric/connect" -Headers $headers -ContentType "application/json" -Body "{}" -TimeoutSec 8
        $evidence.simulation.connect = $connect
        if ($connect.mode -eq "VIRTUAL" -and $connect.reality -eq "SIMULATED") {
            $body = @{ command = "Get-ComputerInfo; Get-Location" } | ConvertTo-Json -Compress
            try {
                $cmd = Invoke-RestMethod -Method Post -Uri "$BrainBaseUrl/api/remote-fabric/simulation/command" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 8
                $evidence.simulation.command = $cmd
                $evidence.simulation.passed = [bool]($cmd.ok -and $cmd.reality -eq "SIMULATED" -and $cmd.mode -eq "VIRTUAL")
            } catch {
                $evidence.simulation.command_error = $_.Exception.Message
                $evidence.simulation.passed = $false
            }
        } else {
            $evidence.simulation.passed = $false
            $evidence.notes += "SIMULATION_MODE_NOT_CONFIRMED; no command sent."
        }
    } catch {
        $evidence.simulation.connect_error = $_.Exception.Message
        $evidence.simulation.passed = $false
    }
} else {
    $evidence.simulation.passed = $false
    $evidence.notes += "CONTROL_KEY_MISSING: GET checks ran; authenticated simulation test was skipped."
}
try {
    New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
    $path = Join-Path $EvidenceDirectory "arkan-live-diagnostics-$stamp.json"
    $evidence | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $path -Encoding UTF8
    Write-Host "Evidence: $path"
} catch {
    Write-Host "EVIDENCE_WRITE_FAILED: $($_.Exception.Message)"
}
Write-Host "=== SUMMARY ==="
Write-Host ("Host: " + $(if ($evidence.host.computer_name) { $evidence.host.computer_name } else { "UNKNOWN" }))
Write-Host ("Brain API readiness: " + $(if ($evidence.api.system_readiness.ok) { "OK" } else { "NOT CONFIRMED" }))
Write-Host ("Simulation command: " + $(if ($evidence.simulation.passed) { "PASS (SIMULATED ONLY)" } else { "NOT PASSED" }))
Write-Host "No secret values were written to the evidence file."

#requires -RunAsAdministrator
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$BrainUrl,
    [string]$PythonExe = "python.exe",
    [string]$AgentSource = (Join-Path $PSScriptRoot "arkan_heartbeat_agent.py"),
    [string]$TaskName = "ElectronicBrain-Arkan-Heartbeat"
)
$ErrorActionPreference = "Stop"
$parsed = [Uri]$BrainUrl
if ($parsed.Scheme -ne "https" -and $parsed.Host -notin @("localhost", "127.0.0.1", "::1")) {
    throw "BRAIN_URL_MUST_USE_HTTPS_UNLESS_LOOPBACK"
}
if (-not (Test-Path -LiteralPath $AgentSource -PathType Leaf)) { throw "AGENT_SOURCE_NOT_FOUND" }
$python = (Get-Command $PythonExe -ErrorAction Stop).Source
$base = Join-Path $env:ProgramData "Brain"
$agentDir = Join-Path $base "agent"
$secretDir = Join-Path $base "secrets"
$keyPath = Join-Path $secretDir "agent.key"
New-Item -ItemType Directory -Force -Path $agentDir,$secretDir | Out-Null
Copy-Item -LiteralPath $AgentSource -Destination (Join-Path $agentDir "arkan_heartbeat_agent.py") -Force

# Only SYSTEM and local Administrators may read/write the Brain directories.
& icacls.exe $base /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "BRAIN_DIRECTORY_ACL_FAILED" }
& icacls.exe $secretDir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "BRAIN_SECRET_DIRECTORY_ACL_FAILED" }

if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) {
    $secure = Read-Host "Enter existing Brain agent key (hidden input)" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
        if ([string]::IsNullOrWhiteSpace($plain) -or $plain.Length -lt 32) { throw "AGENT_KEY_TOO_SHORT" }
        [IO.File]::WriteAllText($keyPath, $plain, [Text.UTF8Encoding]::new($false))
    } finally {
        if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
        $plain = $null
        $secure.Dispose()
    }
}
& icacls.exe $keyPath /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "BRAIN_AGENT_KEY_ACL_FAILED" }

$scriptPath = Join-Path $agentDir "arkan_heartbeat_agent.py"
# The URL is not a secret; the credential stays in the ACL-protected key file.
$arguments = '"{0}" --brain-url "{1}" --key-file "{2}" --agent-id "arkan-windows-agent-01" --interval 10 --max-backoff 120' -f $scriptPath, $BrainUrl.TrimEnd('/'), $keyPath
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $agentDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output "BRAIN_AGENT_INSTALL=CONFIGURED"
Write-Output "BRAIN_AGENT_TASK=$TaskName"
Write-Output "BRAIN_AGENT_ID=arkan-windows-agent-01"
Write-Output "BRAIN_AGENT_MODE=HEARTBEAT_ONLY_READONLY"
Write-Output "BRAIN_AGENT_KEY_PATH=$keyPath"
Write-Output "BRAIN_AGENT_KEY_PRINTED=false"
Write-Output "NEXT_VERIFY=Check task state and recent Brain API heartbeat."

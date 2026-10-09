$ErrorActionPreference = "Stop"
$Root = if ($env:BRAIN_ROOT) { $env:BRAIN_ROOT } else { Join-Path $HOME "MySimpleProject" }
$AgentDir = Join-Path $HOME ".brain-agent"
New-Item -ItemType Directory -Force -Path $AgentDir | Out-Null
$EnvFile = Join-Path $AgentDir "agent.env.ps1"
@"
$env:BRAIN_ROOT = "$Root"
$env:BRAIN_URL = "http://127.0.0.1:8012"
$env:V12_AGENT_ID = "arkan-01"
$env:V12_POLL_SECONDS = "5"
$env:V12_AGENT_KEY_FILE = "$AgentDiragent.key"
"@ | Set-Content -Encoding UTF8 $EnvFile
$Launcher = Join-Path $AgentDir "start-agent.ps1"
@"
$ErrorActionPreference = "Stop"
. "$EnvFile"
Set-Location "$Root"
python "$Rootrain_emulator_agentrain_device_agent_v2.py"
"@ | Set-Content -Encoding UTF8 $Launcher
Write-Host "Brain Windows Agent prepared: $Launcher"

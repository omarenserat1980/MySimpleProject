# Electronic Brain - GitHub Actions Runner diagnostics
# Safe diagnostic: never reads or prints .credentials.
$ErrorActionPreference = "Continue"
$Runner = "C:\actions-runner\actions-runner"
$ExpectedRepo = "https://github.com/omarenserat1980/MySimpleProject"

Write-Host "=== ELECTRONIC BRAIN RUNNER DIAGNOSTIC ===" -ForegroundColor Cyan
Write-Host "RunnerPath=$Runner"
Write-Host "ExpectedRepository=$ExpectedRepo"

foreach ($item in @(".runner", "run.cmd", "config.cmd", "_diag")) {
    Write-Host ("FILE {0}={1}" -f $item, (Test-Path (Join-Path $Runner $item)))
}

$configPath = Join-Path $Runner ".runner"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        $repoUrl = [string]$cfg.gitHubUrl
        if (-not $repoUrl) { $repoUrl = [string]$cfg.serverUrl }
        Write-Host "ConfiguredUrl=$repoUrl"
        Write-Host "RunnerName=$($cfg.agentName)"
        Write-Host "RunnerId=$($cfg.agentId)"
        Write-Host "WorkFolder=$($cfg.workFolder)"
        if ($repoUrl.TrimEnd('/') -ne $ExpectedRepo.TrimEnd('/')) {
            Write-Host "REGISTRATION_URL_MATCH=FALSE" -ForegroundColor Yellow
        } else {
            Write-Host "REGISTRATION_URL_MATCH=TRUE" -ForegroundColor Green
        }
    } catch {
        Write-Host "RUNNER_CONFIG_PARSE=FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "RUNNER_CONFIG=NOT_REGISTERED" -ForegroundColor Yellow
}

$processes = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -like "$Runner*" -or $_.CommandLine -like "*$Runner*" })
Write-Host "RUNNER_PROCESS_COUNT=$($processes.Count)"
$processes | Select-Object Name, ProcessId, ExecutablePath | Format-Table -AutoSize

$services = @(Get-CimInstance Win32_Service -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'actions\.runner' -or $_.DisplayName -match 'GitHub Actions Runner' })
Write-Host "RUNNER_SERVICE_COUNT=$($services.Count)"
$services | Select-Object Name, State, StartMode | Format-Table -AutoSize

$diag = Join-Path $Runner "_diag"
if (Test-Path $diag) {
    $latest = Get-ChildItem $diag -Filter "Runner_*.log" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
        Write-Host "LATEST_RUNNER_LOG=$($latest.Name)"
        Write-Host "LATEST_RUNNER_LOG_TIME=$($latest.LastWriteTime.ToString('o'))"
        $hits = Select-String -LiteralPath $latest.FullName -Pattern 'error|fail|offline|unauthorized|forbidden|connect|session' -CaseSensitive:$false |
            Select-Object -Last 20
        foreach ($hit in $hits) {
            $line = $hit.Line -replace '(?i)(token|authorization|password|secret)(\s*[:=]\s*)\S+', '$1$2[REDACTED]'
            Write-Host ("LOG: " + $line)
        }
    } else {
        Write-Host "RUNNER_LOG=NOT_FOUND"
    }
}
Write-Host "=== DIAGNOSTIC COMPLETE ===" -ForegroundColor Cyan

#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$ProjectRoot = 'C:\Brain\extract\MySimpleProject-brain-software-cloud-pool',
    [int]$Port = 8013
)
$ErrorActionPreference = 'Stop'
$Base = "http://127.0.0.1:$Port"
$LogDir = 'C:\Brain\logs'
$Out = Join-Path $LogDir "cloud-pool-$Port-out.log"
$Err = Join-Path $LogDir "cloud-pool-$Port-error.log"
$Evidence = Join-Path $LogDir "cloud-pool-$Port-status.json"
$Venv = Join-Path $ProjectRoot '.venv'
$Py = Join-Path $Venv 'Scripts\python.exe'
$Req = Join-Path $ProjectRoot 'requirements.txt'
$App = Join-Path $ProjectRoot 'brain_v12\app.py'
$PoolApi = Join-Path $ProjectRoot 'brain_v12\brain\device_cloud_pool_api.py'
$Dashboard = Join-Path $ProjectRoot 'brain_v12\web\cloud-pool.html'
$DashboardUrl = 'https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/brain-software-cloud-pool/brain_v12/web/cloud-pool.html'

try {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host 'Electronic Brain Cloud Pool bootstrap'
    Write-Host "Project: $ProjectRoot"
    Write-Host "Test URL: $Base"
    foreach ($f in @($Req, $App, $PoolApi)) {
        if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { throw "Required file is missing: $f" }
    }
    if (-not (Test-Path -LiteralPath $Dashboard -PathType Leaf)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Dashboard) -Force | Out-Null
        Invoke-WebRequest -Uri $DashboardUrl -OutFile $Dashboard -UseBasicParsing -TimeoutSec 30
    }
    $dashText = Get-Content -LiteralPath $Dashboard -Raw
    if ($dashText -notmatch '/api/cloud-pool/status' -or $dashText -notmatch '/api/hardware/resources') {
        throw 'Dashboard contract check failed.'
    }
    $appText = Get-Content -LiteralPath $App -Raw
    if ($appText -notmatch 'device_cloud_pool_router\s*\(\s*device_cloud_pool\s*\)') {
        throw 'Cloud-pool router registration was not found in brain_v12\app.py.'
    }

    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $listener) {
        if (-not (Test-Path -LiteralPath $Py -PathType Leaf)) {
            & py -3.12 -m venv $Venv
            if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $Py -PathType Leaf)) {
                throw 'Could not create the isolated Python 3.12 environment.'
            }
        }
        & $Py -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed.' }
        & $Py -m pip install -r $Req
        if ($LASTEXITCODE -ne 0) { throw 'Installing root requirements failed.' }
        & $Py -c 'import fastapi, uvicorn, httpx, pydantic'
        if ($LASTEXITCODE -ne 0) { throw 'Required Python imports failed.' }

        Remove-Item -LiteralPath $Out, $Err -Force -ErrorAction SilentlyContinue
        $startArgs = @{
            FilePath = $Py
            ArgumentList = @('-m','uvicorn','brain_v12.app:app','--host','127.0.0.1','--port',"$Port",'--log-level','info')
            WorkingDirectory = $ProjectRoot
            RedirectStandardOutput = $Out
            RedirectStandardError = $Err
            PassThru = $true
        }
        $server = Start-Process @startArgs
        $deadline = (Get-Date).AddSeconds(30)
        do {
            Start-Sleep -Seconds 1
            $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
            if ($listener) { break }
            $server.Refresh()
            if ($server.HasExited) { break }
        } while ((Get-Date) -lt $deadline)
        if (-not $listener) {
            if (Test-Path $Err) { Get-Content $Err -Tail 80 }
            if (Test-Path $Out) { Get-Content $Out -Tail 40 }
            throw "Server did not listen on port $Port. Inspect logs in $LogDir."
        }
    } else {
        Write-Host "Port $Port is already occupied; leaving the existing process untouched."
    }

    $api = Invoke-RestMethod "$Base/openapi.json" -TimeoutSec 15
    $routes = @($api.paths.PSObject.Properties | Where-Object { $_.Name -like '/api/cloud-pool/*' })
    if ($routes.Count -eq 0) { throw "No Cloud Pool routes found on port $Port." }
    $routes | ForEach-Object {
        [PSCustomObject]@{ Path = $_.Name; Methods = ($_.Value.PSObject.Properties.Name -join ', ') }
    } | Format-Table -AutoSize

    $status = Invoke-RestMethod "$Base/api/cloud-pool/status" -TimeoutSec 15
    $status | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Evidence -Encoding UTF8
    $hardware = Invoke-RestMethod "$Base/api/hardware/status" -TimeoutSec 15
    $page = Invoke-WebRequest -Uri "$Base/cloud-pool.html" -UseBasicParsing -TimeoutSec 15
    if ($page.StatusCode -ne 200 -or $page.Content -notmatch 'Electronic Brain') { throw 'Dashboard response validation failed.' }

    Write-Host 'Cloud Pool status:'
    $status | ConvertTo-Json -Depth 12
    Write-Host "Physical source: $($hardware.capacity.source)"
    Write-Host "Physical capacity measured: $($hardware.capacity.observed)"
    Write-Host "Resource semantics: $($hardware.resource_semantics)"
    Write-Host "Evidence: $Evidence"
    Start-Process "$Base/cloud-pool.html"
    Start-Process "$Base/docs"
    Write-Host 'PASS: Dashboard and Cloud Pool API responded. Remote-device enrollment and remote execution are separate checks.' -ForegroundColor Green
}
catch {
    Write-Host "SETUP FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Logs: $LogDir"
    if (Test-Path $Err) { Get-Content $Err -Tail 80 -ErrorAction SilentlyContinue }
    exit 1
}

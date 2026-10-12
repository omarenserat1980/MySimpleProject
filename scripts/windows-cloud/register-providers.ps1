[CmdletBinding()]
param(
    [string[]]$Providers = @("Microsoft.Compute", "Microsoft.Network", "Microsoft.Storage"),
    [int]$TimeoutMinutes = 10
)
$ErrorActionPreference = "Stop"
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI is required."
}
$accountJson = & az account show --output json --only-show-errors 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "Azure CLI is not authenticated. Azure OIDC login must succeed first."
}
try {
    $account = (($accountJson | Out-String).Trim() | ConvertFrom-Json -ErrorAction Stop)
} catch {
    throw "Azure CLI returned invalid account JSON."
}
if (-not $account.id) { throw "Azure CLI has no active subscription." }
if ($env:ARM_SUBSCRIPTION_ID -and $env:ARM_SUBSCRIPTION_ID -ne $account.id) {
    throw "Active Azure subscription does not match ARM_SUBSCRIPTION_ID."
}
foreach ($provider in $Providers) {
    Write-Host "Checking provider registration: $provider"
    $state = (& az provider show --namespace $provider --query registrationState --output tsv --only-show-errors 2>$null | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or -not $state) {
        Write-Host "Requesting registration for $provider"
        & az provider register --namespace $provider --only-show-errors --output none
        if ($LASTEXITCODE -ne 0) {
            throw "Could not request registration for $provider. Check subscription permissions."
        }
    } elseif ($state -ne "Registered") {
        Write-Host "$provider is currently $state; requesting registration."
        & az provider register --namespace $provider --only-show-errors --output none
        if ($LASTEXITCODE -ne 0) {
            throw "Could not request registration for $provider. Check subscription permissions."
        }
    }
}
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
do {
    $states = @{}
    foreach ($provider in $Providers) {
        $state = (& az provider show --namespace $provider --query registrationState --output tsv --only-show-errors 2>$null | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) { $state = "QueryFailed" }
        $states[$provider] = $state
    }
    Write-Host ("Provider states: " + (($Providers | ForEach-Object { "$_=$($states[$_])" }) -join ", "))
    if (@($Providers | Where-Object { $states[$_] -ne "Registered" }).Count -eq 0) {
        Write-Host "Azure provider registration verified. No resource group, storage account, container, or VM was created by this step."
        exit 0
    }
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)
throw "Provider registration did not complete within $TimeoutMinutes minutes. No infrastructure resources were created by this step."

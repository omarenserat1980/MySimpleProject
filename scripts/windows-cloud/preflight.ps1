[CmdletBinding()]
param([string]$Location = "northeurope", [string]$VmSize = "Standard_D4s_v5")
$ErrorActionPreference = "Stop"
function Fail([string]$Message) { throw $Message }
foreach ($tool in @("az","terraform")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "Missing prerequisite: $tool" }
}
$raw = az account show --output json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $raw) { Fail "Azure CLI is not logged in. Use Azure OIDC login first." }
$account = $raw | ConvertFrom-Json
if (-not $account.id) { Fail "Azure CLI has no active subscription." }
if ($env:ARM_SUBSCRIPTION_ID -and $env:ARM_SUBSCRIPTION_ID -ne $account.id) { Fail "Active subscription does not match ARM_SUBSCRIPTION_ID." }
if (-not $env:ARM_CLIENT_ID -or -not $env:ARM_TENANT_ID -or -not $env:ARM_SUBSCRIPTION_ID) { Fail "OIDC configuration incomplete: set ARM_CLIENT_ID, ARM_TENANT_ID and ARM_SUBSCRIPTION_ID as GitHub Actions variables." }
if (-not $env:TF_VAR_admin_username -or -not $env:TF_VAR_admin_password) { Fail "Missing BRAIN_WINDOWS_ADMIN_USERNAME / BRAIN_WINDOWS_ADMIN_PASSWORD secrets. Values are never printed." }
if (-not $env:TF_VAR_allowed_source_ip -or $env:TF_VAR_allowed_source_ip -eq "0.0.0.0/0") { Fail "Set a trusted TF_VAR_allowed_source_ip CIDR. Public-wide management access is forbidden." }
if ($env:TF_VAR_allowed_source_ip -notmatch '^\d{1,3}(\.\d{1,3}){3}/(\d|[12]\d|3[0-2])$') { Fail "TF_VAR_allowed_source_ip must be an IPv4 CIDR." }
$compute = (az provider show --namespace Microsoft.Compute --query registrationState --output tsv 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $compute -ne "Registered") { Fail "Microsoft.Compute is not Registered. Run bootstrap-state.ps1 -RegisterProviders and wait for registration." }
$image = az vm image show --location $Location --urn MicrosoftWindowsServer:WindowsServer:2025-datacenter-azure-edition:latest --query urn --output tsv 2>$null
if ($LASTEXITCODE -ne 0 -or -not $image) { Fail "Windows Server 2025 Marketplace image is not resolvable in $Location." }
$rawSkus = az vm list-skus --location $Location --resource-type virtualMachines --size $VmSize --all --output json 2>$null
if ($LASTEXITCODE -eq 0 -and $rawSkus) {
    $skus = $rawSkus | ConvertFrom-Json
    $eligible = @($skus | Where-Object { $_.name -eq $VmSize -and $_.restrictions.Count -eq 0 })
    if ($eligible.Count -eq 0) { Write-Warning "$VmSize may be restricted or unavailable in $Location. Review SKU restrictions; no automatic region/size change will be made." }
} else { Write-Warning "Could not read SKU metadata; Azure quota and live capacity remain unverified." }
Write-Host "Preflight passed identity, secret presence, provider and image checks."
Write-Host "Subscription: $($account.name) ($($account.id)); region: $Location; requested size: $VmSize"
$match = [regex]::Match($VmSize, '^Standard_[A-Za-z]+(\d+)')
$requiredCores = if ($match.Success) { [int]$match.Groups[1].Value } else { 0 }
$quotaRaw = az vm list-usage --location $Location --output json --only-show-errors 2>$null
if ($LASTEXITCODE -eq 0 -and $quotaRaw) {
    try { $quotas = @($quotaRaw | ConvertFrom-Json) } catch { $quotas = @() }
    $totalQuota = @($quotas | Where-Object { $_.name.value -eq "cores" -or $_.name.localizedValue -match "Total Regional vCPUs" } | Select-Object -First 1)
    $familyQuota = @($quotas | Where-Object { $_.name.value -match "standardDSv5Family" -or $_.name.localizedValue -match "DSv5 Family" } | Select-Object -First 1)
    foreach ($quota in @($totalQuota + $familyQuota)) {
        if ($quota.Count -gt 0 -and $null -ne $quota[0].limit -and $null -ne $quota[0].currentValue) {
            $available = [int]$quota[0].limit - [int]$quota[0].currentValue
            if ($requiredCores -gt 0 -and $available -lt $requiredCores) {
                Fail "Insufficient Azure quota in $Location for ${VmSize}: available=$available, required=$requiredCores, quota=$($quota[0].name.localizedValue). Request quota or select an eligible smaller SKU before applying."
            }
            Write-Host "Quota $($quota[0].name.localizedValue): current=$($quota[0].currentValue), limit=$($quota[0].limit), needed=$requiredCores."
        }
    }
    if ($totalQuota.Count -eq 0 -or $familyQuota.Count -eq 0) {
        Write-Warning "Azure returned quota data but one or more relevant regional/family quotas were not identifiable; review portal quotas before apply."
    }
} else {
    Write-Warning "Azure quota query returned no usable data. Quota remains unverified; review portal quotas before authorizing apply."
}
Write-Host "A SKU listing does not guarantee live capacity; Azure may still reject a deployment."


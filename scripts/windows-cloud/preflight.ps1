[CmdletBinding()]
param([string]$Location = "northeurope", [string]$VmSize = "Standard_D4s_v5")
$ErrorActionPreference = "Stop"
function Fail([string]$Message) { Write-Error $Message; exit 1 }
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
Write-Host "A SKU listing does not guarantee quota or live capacity; Azure may still reject the plan/apply."

[CmdletBinding()]
param(
    [string]$Location = "westeurope",
    [string]$VmSize = "Standard_B1s",
    [switch]$AllowMissingAdminCredentials
)
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
if (-not $env:TF_VAR_admin_username -or -not $env:TF_VAR_admin_password) {
    if ($AllowMissingAdminCredentials) {
        Write-Host "Admin credentials are absent; allowed because this is preflight-only. Deployment remains blocked until both secrets are configured."
    } else {
        Fail "Missing BRAIN_WINDOWS_ADMIN_USERNAME / BRAIN_WINDOWS_ADMIN_PASSWORD secrets. Values are never printed."
    }
}
if (-not $env:TF_VAR_allowed_source_ip -or $env:TF_VAR_allowed_source_ip -eq "0.0.0.0/0") { Fail "Set a trusted TF_VAR_allowed_source_ip CIDR. Public-wide management access is forbidden." }
if ($env:TF_VAR_allowed_source_ip -notmatch '^\d{1,3}(\.\d{1,3}){3}/(\d|[12]\d|3[0-2])$') { Fail "TF_VAR_allowed_source_ip must be an IPv4 CIDR." }
$compute = (az provider show --namespace Microsoft.Compute --query registrationState --output tsv 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $compute -ne "Registered") { Fail "Microsoft.Compute is not Registered. Run bootstrap-state.ps1 -RegisterProviders and wait for registration." }
$imageSkuCandidates = @("2025-datacenter-g2", "2025-datacenter", "2025-datacenter-core-g2", "2025-datacenter-core")
$image = $null
$resolvedSku = $null
$resolvedVersion = $null
$imageLookupErrors = @()
foreach ($candidateSku in $imageSkuCandidates) {
    # Query the regional image catalogue as JSON; some CLI/API combinations return no
    # rows from the version-only JMESPath query even while listing the SKU itself.
    $catalogOutput = & az vm image list --location $Location --publisher MicrosoftWindowsServer --offer WindowsServer --sku $candidateSku --all --output json --only-show-errors 2>&1
    $catalogExitCode = $LASTEXITCODE
    $catalog = @()
    if ($catalogExitCode -eq 0 -and $catalogOutput) {
        try { $catalog = @(($catalogOutput | Out-String | ConvertFrom-Json)) }
        catch {
            $imageLookupErrors += "$candidateSku catalogue JSON parse failed: $($_.Exception.Message)"
            continue
        }
    }
    $versions = @($catalog | Where-Object { $_.sku -eq $candidateSku -and $_.version -match '^\d+(\.\d+){1,3}$' } | Select-Object -ExpandProperty version -Unique)
    if ($versions.Count -eq 0) {
        $detail = ($catalogOutput | Out-String).Trim()
        if (-not $detail) { $detail = "no catalogue entries returned (exit=$catalogExitCode)" }
        $imageLookupErrors += "$candidateSku catalogue => $detail"
        continue
    }
    # Use the catalogue row itself as the authoritative image reference.
    # Avoid `az vm image show --query urn`: some Azure CLI/API versions return null
    # for that derived property even though the catalogue entry is valid.
    $candidateEntries = @($catalog | Where-Object {
        $_.sku -eq $candidateSku -and $_.publisher -eq "MicrosoftWindowsServer" -and
        $_.offer -eq "WindowsServer" -and $_.version -match '^\d+(\.\d+){1,3}$'
    } | Sort-Object { try { [version]$_.version } catch { [version]'0.0' } } -Descending)
    foreach ($entry in $candidateEntries) {
        $candidateVersion = [string]$entry.version
        $candidateImage = [string]$entry.urn
        if (-not $candidateImage -and $entry.publisher -and $entry.offer -and $entry.sku -and $entry.version) {
            $candidateImage = "$($entry.publisher):$($entry.offer):$($entry.sku):$($entry.version)"
        }
        if ($candidateImage -match '^MicrosoftWindowsServer:WindowsServer:[^:]+:\d+(\.\d+){1,3}$') {
            $image = $candidateImage
            $resolvedSku = [string]$entry.sku
            $resolvedVersion = $candidateVersion
            break
        }
        $imageLookupErrors += "$candidateSku version $candidateVersion => catalogue row missing a valid URN and required fields"
    }
    if ($image) { break }
}
if (-not $image) {
    $available2025 = @()
    $rawImages = & az vm image list --location $Location --publisher MicrosoftWindowsServer --offer WindowsServer --all --query "[?contains(sku, '2025')].sku" --output tsv --only-show-errors 2>&1
    $listExitCode = $LASTEXITCODE
    if ($listExitCode -eq 0 -and $rawImages) {
        $available2025 = @($rawImages | ForEach-Object { "$_".Trim() } | Where-Object { $_ -match "2025" } | Sort-Object -Unique)
    }
    $availableText = if ($available2025.Count -gt 0) { $available2025 -join ", " } else { "none returned by Azure CLI (list exit=$listExitCode)" }
    $errorText = if ($imageLookupErrors.Count -gt 0) { $imageLookupErrors -join " | " } else { "Azure CLI returned no detailed image lookup error." }
    Fail "Windows Server 2025 image lookup failed in $Location. Candidate SKUs tried: $($imageSkuCandidates -join ', '). Azure-listed 2025 SKUs: $availableText. Image lookup details: $errorText. Terraform SKU was not changed; no deployment was attempted."
}
Write-Host "Resolved Windows Server image SKU: $resolvedSku (validated version: $resolvedVersion)"
if ($image -notmatch ":${resolvedSku}:") { Fail "Resolved image URN does not match requested Terraform SKU $resolvedSku." }
$rawSkus = az vm list-skus --location $Location --resource-type virtualMachines --size $VmSize --all --output json 2>$null
if ($LASTEXITCODE -eq 0 -and $rawSkus) {
    $skus = $rawSkus | ConvertFrom-Json
    $eligible = @($skus | Where-Object { $_.name -eq $VmSize -and $_.restrictions.Count -eq 0 })
    if ($eligible.Count -eq 0) { Write-Warning "$VmSize may be restricted or unavailable in $Location. Review SKU restrictions; no automatic region/size change will be made." }
} else { Write-Warning "Could not read SKU metadata; Azure quota and live capacity remain unverified." }
Write-Host "Preflight passed identity, secret presence, provider and image checks."
Write-Host "Subscription: $($account.name) ($($account.id)); region: $Location; requested size: $VmSize"
# Derive the exact quota family from the requested SKU. Never accidentally
# check Standard BS Family for a Dsv5 VM (or report a pass on the wrong family).
$requiredCores = 0
$quotaFamilyValue = $null
if ($VmSize -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)_v(\d+)$') {
    $skuPrefix = $Matches[1]
    $skuSuffix = $Matches[3]
    $skuVersion = $Matches[4]
    $quotaFamilyValue = "standard$skuPrefix$skuSuffix" + "v$skuVersion" + "Family"
    $requiredCores = [int]$Matches[2]
} elseif ($VmSize -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)$') {
    $skuPrefix = $Matches[1]
    $skuSuffix = $Matches[3]
    $quotaFamilyValue = "standard$skuPrefix$skuSuffix" + "Family"
    $requiredCores = [int]$Matches[2]
} else {
    Fail "Cannot derive an exact Azure quota family for VM size $VmSize; refusing to report quota readiness."
}
Write-Host "REQUESTED_VM_QUOTA_FAMILY=$quotaFamilyValue"
$quotaRaw = az vm list-usage --location $Location --output json --only-show-errors 2>$null
if ($LASTEXITCODE -ne 0 -or -not $quotaRaw) {
    Fail "Azure quota query returned no usable data. Quota remains unverified; no deployment is authorized."
}
try { $quotas = @($quotaRaw | ConvertFrom-Json) } catch { Fail "Azure quota response was not valid JSON; refusing to report quota readiness." }
$totalQuota = @($quotas | Where-Object { $_.name.value -eq "cores" -or $_.name.localizedValue -match "^Total Regional vCPUs$" } | Select-Object -First 1)
$familyQuota = @($quotas | Where-Object {
    $_.name.value -ieq $quotaFamilyValue -or
    ($_.name.localizedValue -replace '[^A-Za-z0-9]', '') -ieq ($quotaFamilyValue -replace '[^A-Za-z0-9]', '')
} | Select-Object -First 1)
if ($totalQuota.Count -eq 0 -or $familyQuota.Count -eq 0) {
    $foundFamilies = @($quotas | Where-Object { $_.name.value -match 'Family' } | ForEach-Object { $_.name.value } | Where-Object { $_ })
    Fail "Could not identify both regional and exact $quotaFamilyValue quota records in $Location. RegionalFound=$($totalQuota.Count); RequestedFamilyFound=$($familyQuota.Count); returned family records=$($foundFamilies -join ', '). Quota is unverified; no deployment is authorized."
}
foreach ($quota in @($totalQuota[0], $familyQuota[0])) {
    if ($null -eq $quota.limit -or $null -eq $quota.currentValue) {
        Fail "Azure quota record $($quota.name.value) lacks limit/current values; quota is unverified."
    }
    $available = [int]$quota.limit - [int]$quota.currentValue
    if ($available -lt $requiredCores) {
        Fail "Insufficient Azure quota in $Location for $($VmSize): available=$available, required=$requiredCores, quota=$($quota.name.localizedValue). Request quota or select an eligible SKU before applying."
    }
    Write-Host "Quota $($quota.name.localizedValue): current=$($quota.currentValue), limit=$($quota.limit), needed=$requiredCores."
}
Write-Host "A SKU listing does not guarantee live capacity; Azure may still reject a deployment."


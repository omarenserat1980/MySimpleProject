[CmdletBinding()]
param(
    [string]$Location = "westeurope",
    [string]$VmSize = "Standard_B1s",
    [switch]$AllowMissingAdminCredentials
)
$ErrorActionPreference = "Stop"
function Fail([string]$Message) { throw $Message }

foreach ($tool in @("az", "terraform")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Fail "Missing prerequisite: $tool" }
}
$rawAccount = az account show --output json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $rawAccount) { Fail "Azure CLI is not logged in. Use Azure OIDC login first." }
$account = $rawAccount | ConvertFrom-Json
if (-not $account.id) { Fail "Azure CLI has no active subscription." }
if ($env:ARM_SUBSCRIPTION_ID -and $env:ARM_SUBSCRIPTION_ID -ne $account.id) { Fail "Active subscription does not match ARM_SUBSCRIPTION_ID." }
if (-not $env:ARM_CLIENT_ID -or -not $env:ARM_TENANT_ID -or -not $env:ARM_SUBSCRIPTION_ID) { Fail "OIDC configuration incomplete: set ARM_CLIENT_ID, ARM_TENANT_ID and ARM_SUBSCRIPTION_ID as GitHub Actions variables." }

if (-not $env:TF_VAR_admin_username -or -not $env:TF_VAR_admin_password) {
    if ($AllowMissingAdminCredentials) { Write-Host "ADMIN_CREDENTIALS=ABSENT_ALLOWED_FOR_READ_ONLY_PREFLIGHT" }
    else { Fail "Missing BRAIN_WINDOWS_ADMIN_USERNAME / BRAIN_WINDOWS_ADMIN_PASSWORD secrets. Values are never printed." }
}
if (-not $env:TF_VAR_allowed_source_ip -or $env:TF_VAR_allowed_source_ip -eq "0.0.0.0/0") { Fail "Set a trusted TF_VAR_allowed_source_ip CIDR. Public-wide management access is forbidden." }
try {
    $cidrParts = $env:TF_VAR_allowed_source_ip -split "/"
    $sourceIp = [System.Net.IPAddress]::Parse($cidrParts[0])
    $prefix = [int]$cidrParts[1]
    if ($sourceIp.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or $prefix -lt 1 -or $prefix -gt 32) { Fail "TF_VAR_allowed_source_ip must be a valid non-public-wide IPv4 CIDR." }
} catch { Fail "TF_VAR_allowed_source_ip must be a valid IPv4 CIDR." }

$compute = (az provider show --namespace Microsoft.Compute --query registrationState --output tsv 2>$null | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $compute -ne "Registered") { Fail "Microsoft.Compute is not Registered. Register the provider and wait before deployment." }

# Resolve a real Windows Server 2025 image version from the regional catalogue.
$imageSkuCandidates = @("2025-datacenter-g2", "2025-datacenter", "2025-datacenter-core-g2", "2025-datacenter-core")
$image = $null
$resolvedSku = $null
$resolvedVersion = $null
foreach ($candidateSku in $imageSkuCandidates) {
    $catalogOutput = & az vm image list --location $Location --publisher MicrosoftWindowsServer --offer WindowsServer --sku $candidateSku --all --output json --only-show-errors 2>&1
    $catalogExitCode = $LASTEXITCODE
    if ($catalogExitCode -ne 0 -or -not $catalogOutput) { continue }
    try { $catalog = @(($catalogOutput | Out-String | ConvertFrom-Json)) } catch { continue }
    $entries = @($catalog | Where-Object {
        $_.sku -eq $candidateSku -and $_.publisher -eq "MicrosoftWindowsServer" -and
        $_.offer -eq "WindowsServer" -and $_.version -match '^\d+(\.\d+){1,3}$'
    } | Sort-Object { try { [version]$_.version } catch { [version]'0.0' } } -Descending)
    foreach ($entry in $entries) {
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
    }
    if ($image) { break }
}
if (-not $image) {
    $rawImages = & az vm image list --location $Location --publisher MicrosoftWindowsServer --offer WindowsServer --all --query "[?contains(sku, '2025')].sku" --output tsv --only-show-errors 2>&1
    $listExitCode = $LASTEXITCODE
    $available2025 = @()
    if ($listExitCode -eq 0 -and $rawImages) { $available2025 = @($rawImages | ForEach-Object { "$_".Trim() } | Where-Object { $_ -match "2025" } | Sort-Object -Unique) }
    $availableText = if ($available2025.Count -gt 0) { $available2025 -join ", " } else { "none returned by Azure CLI" }
    Fail "Windows Server 2025 image lookup failed in $Location. Azure-listed 2025 SKUs: $availableText. No deployment was attempted."
}
Write-Host "WINDOWS_SERVER_IMAGE_SKU=$resolvedSku"
Write-Host "WINDOWS_SERVER_IMAGE_VERSION=$resolvedVersion"
if ($image -notmatch (":" + [regex]::Escape($resolvedSku) + ":")) { Fail "Resolved image URN does not match the catalogue SKU." }

# Verify exact requested VM size; a family quota does not prove SKU eligibility.
$rawSkus = az vm list-skus --location $Location --resource-type virtualMachines --size $VmSize --all --output json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $rawSkus) { Fail "Could not verify Azure SKU restrictions for $VmSize in $Location. Availability is unverified; no deployment is authorized." }
try { $skus = @($rawSkus | ConvertFrom-Json) } catch { Fail "Azure SKU metadata was not valid JSON; no deployment is authorized." }
$eligible = @($skus | Where-Object { $_.name -eq $VmSize -and @($_.restrictions).Count -eq 0 })
if ($eligible.Count -eq 0) {
    $familyPattern = $null
    $maxCandidateCores = 0
    if ($VmSize -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)_v(\d+)$') {
        $skuPrefix = [string]$Matches[1]
        $maxCandidateCores = [int]$Matches[2]
        $skuSuffix = [string]$Matches[3]
        $skuVersion = [string]$Matches[4]
        $familyPattern = '^Standard_' + [regex]::Escape($skuPrefix) + '\d+' + [regex]::Escape($skuSuffix) + '_v' + [regex]::Escape($skuVersion) + '$'
    } elseif ($VmSize -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)$') {
        $skuPrefix = [string]$Matches[1]
        $maxCandidateCores = [int]$Matches[2]
        $skuSuffix = [string]$Matches[3]
        $familyPattern = '^Standard_' + [regex]::Escape($skuPrefix) + '\d+' + [regex]::Escape($skuSuffix) + '$'
    }
    $candidates = @()
    if ($familyPattern) {
        $allSkusRaw = az vm list-skus --location $Location --resource-type virtualMachines --all --output json 2>$null
        if ($LASTEXITCODE -eq 0 -and $allSkusRaw) {
            try {
                $allSkus = @($allSkusRaw | ConvertFrom-Json)
                $candidates = @(
                    $allSkus |
                    Where-Object { $_.name -match $familyPattern -and @($_.restrictions).Count -eq 0 } |
                    ForEach-Object {
                        $item = $_
                        $coreCapability = @($item.capabilities | Where-Object { $_.name -eq "vCPUs" } | Select-Object -First 1)
                        if ($coreCapability.Count -gt 0) { [pscustomobject]@{ Name = $item.name; Cores = [int]$coreCapability[0].value } }
                    } |
                    Where-Object { $_ -and $_.Cores -le $maxCandidateCores } |
                    Sort-Object Cores, Name |
                    Select-Object -First 10
                )
            } catch { $candidates = @() }
        }
    }
    $candidateText = if ($candidates.Count -gt 0) { ($candidates | ForEach-Object { "$($_.Name) ($($_.Cores) vCPU)" }) -join ", " } else { "none verified in the same VM family; inspect Azure SKU restrictions and quota" }
    Fail "Requested Azure VM size $VmSize is restricted or unavailable in $Location. Eligible same-family candidates with at most $maxCandidateCores vCPUs: $candidateText. No automatic SKU/region change was made; deployment is blocked pending explicit selection."
}
Write-Host "AZURE_VM_SKU_RESTRICTIONS=PASS"

# Derive and verify both regional and exact VM-family quota records.
$requiredCores = 0
$quotaFamilyValue = $null
if ($VmSize -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)_v(\d+)$') {
    $skuPrefix = [string]$Matches[1]
    $requiredCores = [int]$Matches[2]
    $skuSuffix = [string]$Matches[3]
    $skuVersion = [string]$Matches[4]
    $quotaFamilyValue = "standard$skuPrefix$skuSuffix" + "v$skuVersion" + "Family"
} elseif ($VmSize -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)$') {
    $skuPrefix = [string]$Matches[1]
    $requiredCores = [int]$Matches[2]
    $skuSuffix = [string]$Matches[3]
    $quotaFamilyValue = "standard$skuPrefix$skuSuffix" + "Family"
} else { Fail "Cannot derive an exact Azure quota family for VM size $VmSize; refusing quota readiness." }
Write-Host "REQUESTED_VM_QUOTA_FAMILY=$quotaFamilyValue"

$quotaRaw = az vm list-usage --location $Location --output json --only-show-errors 2>$null
if ($LASTEXITCODE -ne 0 -or -not $quotaRaw) { Fail "Azure quota query returned no usable data. Quota remains unverified; no deployment is authorized." }
try { $quotas = @($quotaRaw | ConvertFrom-Json) } catch { Fail "Azure quota response was not valid JSON; refusing quota readiness." }
$totalQuota = @($quotas | Where-Object { $_.name.value -eq "cores" -or $_.name.localizedValue -match "^Total Regional vCPUs$" } | Select-Object -First 1)
$familyQuota = @($quotas | Where-Object {
    $_.name.value -ieq $quotaFamilyValue -or
    (($_.name.localizedValue -replace '[^A-Za-z0-9]', '') -ieq ($quotaFamilyValue -replace '[^A-Za-z0-9]', ''))
} | Select-Object -First 1)
if ($totalQuota.Count -eq 0 -or $familyQuota.Count -eq 0) {
    $foundFamilies = @($quotas | Where-Object { $_.name.value -match "Family" } | ForEach-Object { $_.name.value } | Where-Object { $_ })
    Fail "Could not identify both regional and exact $quotaFamilyValue quota records in $Location. RegionalFound=$($totalQuota.Count); RequestedFamilyFound=$($familyQuota.Count); returned family records=$($foundFamilies -join ', '). Quota is unverified."
}
foreach ($quota in @($totalQuota[0], $familyQuota[0])) {
    if ($null -eq $quota.limit -or $null -eq $quota.currentValue) { Fail "Azure quota record $($quota.name.value) lacks limit/current values; quota is unverified." }
    $available = [int]$quota.limit - [int]$quota.currentValue
    if ($available -lt $requiredCores) { Fail "Insufficient Azure quota in $Location for VM size $VmSize; available=$available, required=$requiredCores, quota=$($quota.name.localizedValue). No apply was attempted." }
    Write-Host "Quota $($quota.name.localizedValue): current=$($quota.currentValue), limit=$($quota.limit), needed=$requiredCores."
}
Write-Host "AZURE_OIDC_ACCOUNT_CHECK=PASS"
Write-Host "AZURE_VM_SKU_RESTRICTIONS=PASS"
Write-Host "AZURE_QUOTA_CHECK=PASS"
Write-Host "A SKU listing does not guarantee live capacity; Azure may still reject a deployment."
Write-Host "PREFLIGHT_ONLY=TRUE"
Write-Host "AZURE_RESOURCE_CREATION=NOT_ATTEMPTED"
Write-Host "WINDOWS_SERVER_2025_BOOT=NOT_VERIFIED"

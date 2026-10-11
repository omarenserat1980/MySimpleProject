[CmdletBinding()]
param(
    [string[]]$Locations = @("northeurope", "westeurope", "uksouth", "swedencentral", "francecentral", "polandcentral", "eastus2", "centralus"),
    [string[]]$VmSizes = @("Standard_D2s_v5", "Standard_D4s_v5", "Standard_D2s_v4", "Standard_D4s_v4", "Standard_B2s", "Standard_B2ms")
)
$ErrorActionPreference = "Stop"

function Get-QuotaFamily([string]$Size) {
    if ($Size -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)_v(\d+)$') {
        return "standard$($Matches[1])$($Matches[3])v$($Matches[4])Family"
    }
    if ($Size -match '^Standard_([A-Za-z]+?)(\d+)([A-Za-z]*)$') {
        return "standard$($Matches[1])$($Matches[3])Family"
    }
    return $null
}
function Get-RequiredCores([string]$Size) {
    if ($Size -match '^Standard_[A-Za-z]+?(\d+)[A-Za-z]*(?:_v\d+)?$') { return [int]$Matches[1] }
    return 0
}

$account = az account show --output json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $account) { throw "Azure CLI login required for read-only SKU discovery." }
$accountObject = $account | ConvertFrom-Json
if ($env:ARM_SUBSCRIPTION_ID -and $accountObject.id -ne $env:ARM_SUBSCRIPTION_ID) { throw "Azure subscription mismatch; refusing discovery." }

$results = @()
foreach ($location in $Locations) {
    Write-Host "SKU_DISCOVERY_REGION=$location"
    $usageRaw = az vm list-usage --location $location --output json --only-show-errors 2>$null
    $usageOk = ($LASTEXITCODE -eq 0 -and $usageRaw)
    $usage = @()
    if ($usageOk) {
        try { $usage = @($usageRaw | ConvertFrom-Json) } catch { $usageOk = $false }
    }
    $regionalQuota = @($usage | Where-Object {
        $_.name.value -eq "cores" -or $_.name.localizedValue -match "^Total Regional vCPUs$"
    } | Select-Object -First 1)

    foreach ($size in $VmSizes) {
        $cores = Get-RequiredCores $size
        $family = Get-QuotaFamily $size
        if ($cores -le 0 -or -not $family) { continue }
        $skuRaw = az vm list-skus --location $location --resource-type virtualMachines --size $size --all --output json --only-show-errors 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $skuRaw) {
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=UNVERIFIED,REASON=SKU_QUERY_FAILED"
            continue
        }
        try { $skuRows = @($skuRaw | ConvertFrom-Json) } catch {
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=UNVERIFIED,REASON=INVALID_SKU_JSON"
            continue
        }
        $match = @($skuRows | Where-Object { $_.name -eq $size } | Select-Object -First 1)
        if ($match.Count -eq 0) {
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=UNAVAILABLE,REASON=SKU_NOT_LISTED"
            continue
        }
        if (@($match[0].restrictions).Count -gt 0) {
            $restrictionText = @($match[0].restrictions | ForEach-Object { $_.reasonCode }) -join ";"
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=RESTRICTED,REASON=$restrictionText"
            continue
        }
        if (-not $usageOk -or $regionalQuota.Count -eq 0) {
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=UNVERIFIED,REASON=REGIONAL_QUOTA_UNAVAILABLE"
            continue
        }
        $familyQuota = @($usage | Where-Object {
            $_.name.value -ieq $family -or
            (($_.name.localizedValue -replace '[^A-Za-z0-9]', '') -ieq ($family -replace '[^A-Za-z0-9]', ''))
        } | Select-Object -First 1)
        if ($familyQuota.Count -eq 0) {
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=UNVERIFIED,REASON=FAMILY_QUOTA_NOT_FOUND,FAMILY=$family"
            continue
        }
        $regionalAvailable = [int]$regionalQuota[0].limit - [int]$regionalQuota[0].currentValue
        $familyAvailable = [int]$familyQuota[0].limit - [int]$familyQuota[0].currentValue
        if ($regionalAvailable -lt $cores -or $familyAvailable -lt $cores) {
            Write-Host "SKU_CANDIDATE=$location,$size,STATUS=INSUFFICIENT_QUOTA,REGIONAL_AVAILABLE=$regionalAvailable,FAMILY_AVAILABLE=$familyAvailable,NEEDED=$cores"
            continue
        }
        $results += [pscustomobject]@{ Location = $location; Size = $size; Cores = $cores; Family = $family; RegionalAvailable = $regionalAvailable; FamilyAvailable = $familyAvailable }
        Write-Host "SKU_CANDIDATE=$location,$size,STATUS=ELIGIBLE_FOR_FURTHER_PREFLIGHT,REGIONAL_AVAILABLE=$regionalAvailable,FAMILY_AVAILABLE=$familyAvailable"
    }
}
Write-Host "SKU_DISCOVERY_ELIGIBLE_COUNT=$($results.Count)"
if ($results.Count -gt 0) {
    $results | Sort-Object Cores, Location, Size | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host "NOTE=Eligibility and quota are not a guarantee of live capacity or Windows image availability."
    Write-Host "NOTE=No deployment defaults were changed and no Azure resources were created."
} else {
    Write-Host "NO_ELIGIBLE_CANDIDATES_VERIFIED=TRUE"
    Write-Host "NOTE=No region or VM size was changed; investigate quota, SKU restrictions, subscription policy, and regional availability."
}

[CmdletBinding()]
param(
    [string]$Location = "northeurope",
    [string]$ResourceGroup = "brain-tfstate-rg",
    [string]$Container = "tfstate",
    [switch]$RegisterProviders
)
$ErrorActionPreference = "Stop"
function Invoke-AzJson([string[]]$AzArguments) {
    # Azure CLI can emit WARNING/INFO text on the same stream as JSON. Keep
    # the exit-code check, then parse only the JSON object rather than feeding
    # the diagnostic prefix to ConvertFrom-Json.
    $raw = & az @AzArguments --only-show-errors 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        $diagnostic = ($raw | Out-String).Trim()
        throw "Azure CLI failed (exit $exitCode): az $($AzArguments -join ' '). $diagnostic"
    }
    $text = ($raw | ForEach-Object { "$_" }) -join "`n"
    $text = $text.Trim()
    if (-not $text) { return $null }

    $start = $text.IndexOf('{')
    $end = $text.LastIndexOf('}')
    if ($start -lt 0 -or $end -lt $start) {
        throw "Azure CLI returned no JSON object for: az $($AzArguments -join ' '). Check Azure CLI output and authentication."
    }
    $jsonText = $text.Substring($start, $end - $start + 1)
    try {
        return ($jsonText | ConvertFrom-Json -ErrorAction Stop)
    } catch {
        throw "Azure CLI returned malformed JSON for: az $($AzArguments -join ' '). $($_.Exception.Message)"
    }
}
if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "Azure CLI is required." }
$account = Invoke-AzJson @("account","show","--output","json")
$subscriptionId = $account.id
if ($env:ARM_SUBSCRIPTION_ID -and $env:ARM_SUBSCRIPTION_ID -ne $subscriptionId) { throw "Active Azure subscription does not match ARM_SUBSCRIPTION_ID." }
if ($RegisterProviders) {
    foreach ($provider in @("Microsoft.Compute","Microsoft.Network","Microsoft.Storage")) {
        Write-Host "Requesting registration for $provider..."
        & az provider register --namespace $provider --output none
        if ($LASTEXITCODE -ne 0) { throw "Could not request registration for $provider." }
    }
    $deadline = (Get-Date).AddMinutes(10)
    do {
        $states = @{}
        foreach ($provider in @("Microsoft.Compute","Microsoft.Network","Microsoft.Storage")) {
            $states[$provider] = (& az provider show --namespace $provider --query registrationState --output tsv 2>$null | Out-String).Trim()
        }
        Write-Host ("Provider states: " + (($states.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ", "))
        if (@($states.Values | Where-Object { $_ -ne "Registered" }).Count -eq 0) { break }
        Start-Sleep -Seconds 10
    } while ((Get-Date) -lt $deadline)
    if (@($states.Values | Where-Object { $_ -ne "Registered" }).Count -gt 0) { throw "Provider registration incomplete. Check Azure RBAC and portal status." }
}
$derived = "brainstate" + ($subscriptionId.Replace("-","").Substring(0,14)).ToLowerInvariant()
$storageAccount = if ($env:BRAIN_TFSTATE_ACCOUNT) { $env:BRAIN_TFSTATE_ACCOUNT.ToLowerInvariant() } else { $derived }
if ($storageAccount.Length -lt 3 -or $storageAccount.Length -gt 24 -or $storageAccount -notmatch '^[a-z0-9]+$') { throw "BRAIN_TFSTATE_ACCOUNT must be 3-24 lowercase letters/numbers." }
$null = & az group show --name $ResourceGroup --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating dedicated state resource group $ResourceGroup in $Location."
    & az group create --name $ResourceGroup --location $Location --tags project=ElectronicBrain purpose=terraform-state --output none
    if ($LASTEXITCODE -ne 0) { throw "Could not create state resource group." }
}
$null = & az storage account show --name $storageAccount --resource-group $ResourceGroup --output none 2>$null
if ($LASTEXITCODE -ne 0) {
    $check = Invoke-AzJson @("storage","account","check-name","--name",$storageAccount,"--output","json")
    if (-not $check.nameAvailable) { throw "State storage name $storageAccount is unavailable. Set BRAIN_TFSTATE_ACCOUNT to a globally unique valid name." }
    Write-Host "Creating private Standard_LRS state storage $storageAccount."
    & az storage account create --name $storageAccount --resource-group $ResourceGroup --location $Location --sku Standard_LRS --kind StorageV2 --https-only true --min-tls-version TLS1_2 --allow-blob-public-access false --tags project=ElectronicBrain purpose=terraform-state --output none
    if ($LASTEXITCODE -ne 0) { throw "State storage creation failed; check quota, policy, and RBAC." }
}
& az storage container create --name $Container --account-name $storageAccount --auth-mode login --public-access off --output none
if ($LASTEXITCODE -ne 0) { throw "State container access failed. Grant Storage Blob Data Contributor to the OIDC identity." }
[ordered]@{
    subscription_id = $subscriptionId
    state_resource_group = $ResourceGroup
    state_location = $Location
    storage_account = $storageAccount
    container = $Container
    state_key = "brain-windows-2025.tfstate"
    auth = "OIDC / Azure AD; no storage keys"
} | ConvertTo-Json | Write-Output

param(
  [string]$Location = "eastus",
  [string]$ImageUrn = "MicrosoftWindowsServer:WindowsServer:2025-datacenter-azure-edition:latest"
)
$ErrorActionPreference = "Stop"
$account = az account show --output json | ConvertFrom-Json
$usage = az vm list-usage --location $Location --output json | ConvertFrom-Json
$regional = $usage | Where-Object { $_.name.value -eq "cores" } | Select-Object -First 1
$image = az vm image show --location $Location --urn $ImageUrn --output json | ConvertFrom-Json
$evidence = [ordered]@{
  schema = "BRAIN-REAL-AZURE-PREFLIGHT-1"
  read_only = $true
  subscription_id = $account.id
  location = $Location
  regional_vcpu_current = [int]$regional.currentValue
  regional_vcpu_limit = [int]$regional.limit
  windows_server_2025 = $true
  architecture = $image.architecture
  image_state = $image.imageDeprecationStatus.imageState
  image_id = $image.id
  provisioning_allowed = $false
  cost_verified_zero = $false
  reason = "Azure control-plane quota/image evidence is available, but zero-cost entitlement is not independently proven; provisioning remains blocked."
}
$evidence | ConvertTo-Json -Depth 8

[CmdletBinding()]
param(
    [switch]$Apply,
    [switch]$SkipConfirmation,
    [string]$Location = "northeurope",
    [string]$ResourceGroup = "brain-windows-rg",
    [string]$VmName = "brain-windows-2025",
    [string]$VmSize = "Standard_D4s_v5",
    [string]$AllowedSourceIp = "212.34.20.123/32",
    [string]$StateResourceGroup = "brain-tfstate-rg",
    [string]$StateContainer = "tfstate"
)
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$tfDir = Join-Path $repoRoot "brain_v12/cloud/windows_terraform"
$preflight = Join-Path $PSScriptRoot "preflight.ps1"
$verify = Join-Path $PSScriptRoot "verify.ps1"
$configure = Join-Path $PSScriptRoot "configure-winrm.ps1"
if (-not (Test-Path $tfDir)) { throw "Terraform directory not found: $tfDir" }
$env:TF_IN_AUTOMATION = "true"
$env:TF_INPUT = "false"
$env:ARM_USE_OIDC = "true"
$env:TF_VAR_resource_group_location = $Location
$env:TF_VAR_resource_group_name = $ResourceGroup
$env:TF_VAR_vm_name = $VmName
$env:TF_VAR_vm_size = $VmSize
$env:TF_VAR_allowed_source_ip = $AllowedSourceIp
if (-not $env:TF_VAR_admin_username -or -not $env:TF_VAR_admin_password) {
    throw "Set TF_VAR_admin_username and TF_VAR_admin_password from GitHub environment secrets. Never put credentials in files or command-line arguments."
}
& $preflight -Location $Location -VmSize $VmSize
if ($LASTEXITCODE -ne 0) { throw "Preflight failed." }
$stateAccount = if ($env:BRAIN_TFSTATE_ACCOUNT) { $env:BRAIN_TFSTATE_ACCOUNT } else { "brainstate" + ($env:ARM_SUBSCRIPTION_ID.Replace("-","").Substring(0,14)).ToLowerInvariant() }
Push-Location $tfDir
try {
    & terraform init -input=false -reconfigure "-backend-config=resource_group_name=$StateResourceGroup" "-backend-config=storage_account_name=$stateAccount" "-backend-config=container_name=$StateContainer" "-backend-config=key=$VmName.tfstate" "-backend-config=use_oidc=true" "-backend-config=use_azuread_auth=true" "-backend-config=subscription_id=$env:ARM_SUBSCRIPTION_ID" "-backend-config=tenant_id=$env:ARM_TENANT_ID" "-backend-config=client_id=$env:ARM_CLIENT_ID"
    if ($LASTEXITCODE -ne 0) { throw "Terraform init/backend failed. Bootstrap state and grant Storage Blob Data Contributor." }
    & terraform validate
    if ($LASTEXITCODE -ne 0) { throw "Terraform validation failed." }
    # Keep the plan artifact aligned with TerraformPlanGate.
    $planPath = Join-Path $tfDir "brain.tfplan"
    & terraform plan -input=false -out=$planPath
    if ($LASTEXITCODE -ne 0) { throw "Terraform plan failed. No apply was attempted." }
    if (-not $Apply) {
        Write-Host "PLAN READY: $planPath"
        Write-Host "Plan-only mode: no VM resources were created or changed."
        return
    }
    if (-not $SkipConfirmation) {
        $answer = Read-Host "This will create/change Azure resources in $Location. Type APPLY to continue"
        if ($answer -cne "APPLY") { throw "Apply cancelled." }
    }
    & terraform apply -input=false $planPath
    if ($LASTEXITCODE -ne 0) { throw "Terraform apply failed. Inspect Azure Activity Log and remote Terraform state before retrying." }
} finally { Pop-Location }
Write-Host "Waiting for Azure to confirm the VM is running..."
$deadline = (Get-Date).AddMinutes(10)
$vm = $null
do {
    $raw = az vm show --resource-group $ResourceGroup --name $VmName --show-details --output json 2>$null
    if ($LASTEXITCODE -eq 0 -and $raw) {
        $vm = $raw | ConvertFrom-Json
        if ($vm.provisioningState -eq "Succeeded" -and $vm.powerState -eq "VM running") { break }
    }
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)
if (-not $vm -or $vm.provisioningState -ne "Succeeded" -or $vm.powerState -ne "VM running") { throw "Azure did not confirm a successfully provisioned running VM. Launch is not verified." }
$scriptText = Get-Content $configure -Raw
& az vm run-command invoke --resource-group $ResourceGroup --name $VmName --command-id RunPowerShellScript --scripts $scriptText --parameters "AllowedSourceIp=$AllowedSourceIp" --output none
if ($LASTEXITCODE -ne 0) { throw "Azure Run Command could not configure WinRM HTTPS. VM may run, but launch is not verified." }
$env:BRAIN_ADMIN_USERNAME = $env:TF_VAR_admin_username
$env:BRAIN_ADMIN_PASSWORD = $env:TF_VAR_admin_password
& $verify -ResourceGroup $ResourceGroup -VmName $VmName
if ($LASTEXITCODE -ne 0) { throw "Final verification failed. Launch is not successful." }
Write-Host "SUCCESS: Azure reports the VM running and authenticated WinRM verification passed."

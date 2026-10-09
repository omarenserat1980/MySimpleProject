[CmdletBinding()]
param(
    [string]$ResourceGroup = "brain-windows-rg",
    [string]$VmName = "brain-windows-2025",
    [string]$SubscriptionId
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# READ-ONLY: never creates, starts, stops, reconfigures, or deletes Azure resources.
# Never prints tokens, passwords, client secrets, or private key material.
$report = [ordered]@{
    diagnostic = "BRAIN_AZURE_WINDOWS_READONLY"
    timestampUtc = [DateTime]::UtcNow.ToString("o")
    readOnly = $true
    subscription = $null
    resourceGroup = $ResourceGroup
    vmName = $VmName
    checks = [System.Collections.Generic.List[object]]::new()
    findings = [System.Collections.Generic.List[string]]::new()
    nextStep = "REVIEW_FINDINGS"
}
function Add-Check([string]$Name, [string]$Status, [string]$Detail) {
    $report.checks.Add([ordered]@{ name=$Name; status=$Status; detail=$Detail })
}
function Invoke-AzJson([string[]]$Arguments) {
    $allArgs = @($Arguments) + @("--output", "json", "--only-show-errors")
    $raw = & az @allArgs 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($raw -join [Environment]::NewLine))) { return $null }
    try { return (($raw -join [Environment]::NewLine) | ConvertFrom-Json -Depth 30) } catch { return $null }
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Add-Check "azure_cli" "BLOCKED" "Azure CLI is not installed or not on PATH."
    $report.findings.Add("Install Azure CLI from Microsoft, then sign in interactively. This script does not install software.")
    $report.nextStep = "AZURE_CLI_UNAVAILABLE"
    $report | ConvertTo-Json -Depth 30
    exit 2
}
Add-Check "azure_cli" "PASS" "Azure CLI command found."

$accountArgs = @("account","show","--query","{subscriptionId:id,subscriptionName:name,tenantId:tenantId,userType:user.type,state:state}")
if ($SubscriptionId) { $accountArgs = @("account","show","--subscription",$SubscriptionId,"--query","{subscriptionId:id,subscriptionName:name,tenantId:tenantId,userType:user.type,state:state}") }
$account = Invoke-AzJson $accountArgs
if (-not $account) {
    Add-Check "azure_authentication" "BLOCKED" "No usable Azure CLI login for the selected subscription."
    $report.findings.Add("In a trusted terminal, run az login interactively and rerun this diagnostic. Never paste access tokens or passwords into chat.")
    $report.nextStep = "AZURE_LOGIN_REQUIRED"
    $report | ConvertTo-Json -Depth 30
    exit 3
}
$report.subscription = $account
Add-Check "azure_authentication" "PASS" "Azure CLI returned account context; no credentials were requested."
if ($account.state -and $account.state -ne "Enabled") { Add-Check "subscription_state" "WARN" "Subscription state is '$($account.state)'." }

$groupArgs = @("group","exists","--name",$ResourceGroup)
if ($SubscriptionId) { $groupArgs += @("--subscription",$SubscriptionId) }
$groupResult = & az @groupArgs --only-show-errors 2>$null
$groupExists = ($LASTEXITCODE -eq 0 -and (($groupResult -join "").Trim() -eq "true"))
if (-not $groupExists) {
    Add-Check "resource_group" "NOT_FOUND_OR_UNREADABLE" "Resource group not found in selected subscription, or Azure denied the read."
    $report.findings.Add("Check subscription and Azure Portal resource groups. Do not create a replacement group yet.")
    $report.nextStep = "CHECK_SUBSCRIPTION_AND_RESOURCE_GROUP"
    $report | ConvertTo-Json -Depth 30
    exit 0
}
Add-Check "resource_group" "PASS" "Resource group exists."

$vmQuery = "{id:id,name:name,location:location,vmSize:hardwareProfile.vmSize,provisioningState:provisioningState,osType:storageProfile.osDisk.osType,networkInterfaceIds:networkProfile.networkInterfaces[].id}"
$vmArgs = @("vm","show","--resource-group",$ResourceGroup,"--name",$VmName,"--query",$vmQuery)
if ($SubscriptionId) { $vmArgs += @("--subscription",$SubscriptionId) }
$vm = Invoke-AzJson $vmArgs
if (-not $vm) {
    Add-Check "virtual_machine" "NOT_FOUND_OR_UNREADABLE" "VM was not returned in the selected resource group."
    $report.findings.Add("Inspect Activity log and resource groups in the correct subscription. A failed read is not proof that no VM exists.")
    $report.nextStep = "VM_NOT_CONFIRMED"
    $report | ConvertTo-Json -Depth 30
    exit 0
}
$report.vm = $vm
Add-Check "virtual_machine" "PASS" "Azure returned VM metadata."
if ($vm.provisioningState -ne "Succeeded") { Add-Check "provisioning_state" "WARN" "Provisioning state is '$($vm.provisioningState)'." }

$powerArgs = @("vm","get-instance-view","--resource-group",$ResourceGroup,"--name",$VmName,"--query","instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus | [0]")
if ($SubscriptionId) { $powerArgs += @("--subscription",$SubscriptionId) }
$power = & az @powerArgs --output tsv --only-show-errors 2>$null
if ($LASTEXITCODE -eq 0 -and $power) {
    $report.powerState = ($power -join "").Trim()
    if ($report.powerState -eq "VM running") { Add-Check "power_state" "PASS" "VM is running." }
    else {
        Add-Check "power_state" "WARN" "Power state is '$($report.powerState)'; this diagnostic will not start it."
        $report.findings.Add("Review state and expected cost before deciding whether to start the VM.")
    }
} else { Add-Check "power_state" "UNKNOWN" "Azure did not return an instance power state." }

$nicArgs = @("network","nic","list","--resource-group",$ResourceGroup,"--query","[].{name:name,privateIp:ipConfigurations[0].privateIPAddress,publicIpId:ipConfigurations[0].publicIPAddress.id,nsgId:networkSecurityGroup.id}")
if ($SubscriptionId) { $nicArgs += @("--subscription",$SubscriptionId) }
$nics = Invoke-AzJson $nicArgs
$report.networkInterfaces = @($nics)
if ($nics) { Add-Check "network_interfaces" "PASS" "Read network interface metadata." }
else { Add-Check "network_interfaces" "WARN" "No NIC metadata returned; check permissions and VM network attachment." }

$publicIps = [System.Collections.Generic.List[object]]::new()
foreach ($nic in @($nics)) {
    if (-not $nic.publicIpId) { continue }
    $parts = $nic.publicIpId -split "/"
    $pipName = $parts[-1]
    $rgIndex = [Array]::IndexOf($parts,"resourceGroups")
    if ($rgIndex -lt 0 -or $parts.Length -le ($rgIndex + 1)) { continue }
    $pipRg = $parts[$rgIndex + 1]
    $pipArgs = @("network","public-ip","show","--resource-group",$pipRg,"--name",$pipName,"--query","{name:name,ipAddress:ipAddress,allocationMethod:publicIPAllocationMethod}")
    if ($SubscriptionId) { $pipArgs += @("--subscription",$SubscriptionId) }
    $pip = Invoke-AzJson $pipArgs
    if ($pip) { $publicIps.Add($pip) }
}
$report.publicIps = @($publicIps)
Add-Check "public_ip" "INFO" "Resolved $($publicIps.Count) public IP resource(s). Presence does not prove reachability."

# Inspect effective NSG for NICs attached to the VM, including NICs in other resource groups.
$effectiveNsg = [System.Collections.Generic.List[object]]::new()
foreach ($nicId in @($vm.networkInterfaceIds)) {
    if (-not $nicId) { continue }
    $effArgs = @("network","nic","list-effective-nsg","--ids",$nicId)
    if ($SubscriptionId) { $effArgs += @("--subscription",$SubscriptionId) }
    $eff = Invoke-AzJson $effArgs
    $effectiveNsg.Add([ordered]@{ nicId=$nicId; result=$eff })
}
$report.effectiveNetworkSecurityGroups = @($effectiveNsg)
Add-Check "effective_network_security_groups" "INFO" "Requested effective NSG data for VM-attached NICs. Missing results may mean insufficient permissions or API limitations."

# Discover Bastion anywhere in the selected subscription without creating anything.
$bastionArgs = @("network","bastion","list","--query","[].{name:name,resourceGroup:resourceGroup,location:location,provisioningState:provisioningState,sku:sku.name}")
if ($SubscriptionId) { $bastionArgs += @("--subscription",$SubscriptionId) }
$report.bastionHosts = @(Invoke-AzJson $bastionArgs)
if (@($report.bastionHosts).Count -gt 0) { Add-Check "bastion" "INFO" "Bastion resource(s) found in selected subscription. Confirm status, VNet connectivity, and existing billing before use." }
else { Add-Check "bastion" "INFO" "No Bastion resource was returned for selected subscription, or the read failed." }

# Recent activity log is read-only and can explain failed provisioning/deletion.
$activityArgs = @("monitor","activity-log","list","--resource-group",$ResourceGroup,"--offset","30d","--max-events","50","--query","[].{eventTimestamp:eventTimestamp,operationName:operationName.value,status:status.value,subStatus:subStatus.value,resourceId:resourceId,caller:caller}")
if ($SubscriptionId) { $activityArgs += @("--subscription",$SubscriptionId) }
$report.recentActivity = @(Invoke-AzJson $activityArgs)
Add-Check "activity_log" "INFO" "Read up to 50 activity events for the last 30 days in the target resource group. An empty result may reflect retention, scope, or permissions."

$report.findings.Add("Inventory only: no resource changes, port probes, start/stop, NSG edits, Bastion creation, subscription switching, or billing estimates were performed.")
$report.findings.Add("A successful control-plane read does not prove Windows is booted, RDP is enabled, credentials are valid, or a network path is reachable.")
$report.nextStep = "REVIEW_VM_STATE_EFFECTIVE_NETWORK_AND_ACTIVITY_LOG"
$report | ConvertTo-Json -Depth 30

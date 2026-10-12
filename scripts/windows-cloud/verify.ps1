[CmdletBinding()]
param(
    [string]$ResourceGroup = "brain-windows-rg",
    [string]$VmName = "brain-windows-2025",
    [int]$TimeoutSeconds = 600
)
$ErrorActionPreference = "Stop"
function Fail([string]$Message) { throw $Message }
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$vm = $null
do {
    $raw = az vm show --resource-group $ResourceGroup --name $VmName --show-details --output json 2>$null
    if ($LASTEXITCODE -eq 0 -and $raw) { $vm = $raw | ConvertFrom-Json; break }
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)
if (-not $vm) { Fail "VM_NOT_FOUND: Azure does not report $VmName in $ResourceGroup." }
if ([string]$vm.provisioningState -ne "Succeeded") { Fail "VM_PROVISIONING_NOT_SUCCEEDED: Azure reports '$($vm.provisioningState)'." }
if ([string]$vm.powerState -ne "VM running") { Fail "VM_NOT_RUNNING: Azure reports '$($vm.powerState)'." }
$ip = [string]$vm.publicIps
if (-not $ip) { Fail "NO_PUBLIC_IP: VM is running but has no public IP to test." }

# Do not probe restricted management ports from the hosted GitHub runner:
# its egress IP is not the user's ASUS/Arkan IP. Verify NSG policy instead.
$nsgRaw = az network nsg rule list --resource-group $ResourceGroup --nsg-name "$VmName-nsg" --output json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $nsgRaw) { Fail "NSG_RULES_NOT_READABLE: unable to inspect the VM network security group." }
$nsgRules = @($nsgRaw | ConvertFrom-Json)
$rdpRule = $nsgRules | Where-Object { $_.name -eq "AllowRDP" } | Select-Object -First 1
$winrmRule = $nsgRules | Where-Object { $_.name -eq "AllowWinRM" } | Select-Object -First 1
if (-not $rdpRule -or [string]$rdpRule.destinationPortRange -ne "3389") { Fail "RDP_NSG_RULE_MISSING: AllowRDP TCP 3389 rule was not found." }
if (-not $winrmRule -or [string]$winrmRule.destinationPortRange -ne "5986") { Fail "WINRM_NSG_RULE_MISSING: AllowWinRM TCP 5986 rule was not found." }
$expectedSource = [string]$env:TF_VAR_allowed_source_ip
if (-not $expectedSource) { Fail "EXPECTED_SOURCE_CIDR_MISSING: trusted source CIDR is not available to verification." }
foreach ($rule in @($rdpRule,$winrmRule)) {
    $source = [string]$rule.sourceAddressPrefix
    if (-not $source -or $source -in @("*","0.0.0.0/0","Internet")) {
        Fail "OPEN_MANAGEMENT_SOURCE: rule '$($rule.name)' is not restricted to the trusted source CIDR."
    }
    if ($source -ne $expectedSource) {
        Fail "MANAGEMENT_SOURCE_MISMATCH: rule '$($rule.name)' does not match the configured trusted source CIDR."
    }
}

$guestScript = @'
$os = Get-CimInstance Win32_OperatingSystem
$rdpSetting = (Get-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name fDenyTSConnections).fDenyTSConnections
$term = Get-Service -Name TermService -ErrorAction SilentlyContinue
$rdpRule = Get-NetFirewallRule -DisplayName "Electronic Brain RDP" -ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq "True" -and $_.Direction -eq "Inbound" -and $_.Action -eq "Allow" } | Select-Object -First 1
$rdpPort = Get-NetTCPConnection -State Listen -LocalPort 3389 -ErrorAction SilentlyContinue | Select-Object -First 1
$winrmRule = Get-NetFirewallRule -DisplayName "Electronic Brain WinRM HTTPS" -ErrorAction SilentlyContinue | Where-Object { $_.Enabled -eq "True" -and $_.Direction -eq "Inbound" -and $_.Action -eq "Allow" } | Select-Object -First 1
$httpsListener = Get-ChildItem WSMan:\Localhost\Listener | Where-Object { try { (Get-Item "$($_.PSPath)\Transport" -ErrorAction Stop).Value -eq "HTTPS" } catch { $false } } | Select-Object -First 1
[ordered]@{
  computer = $env:COMPUTERNAME
  os = $os.Caption
  architecture = $os.OSArchitecture
  last_boot_utc = $os.LastBootUpTime.ToUniversalTime().ToString("o")
  rdp_enabled = ($rdpSetting -eq 0)
  termservice_running = ([string]$term.Status -eq "Running")
  rdp_firewall_rule_enabled = [bool]$rdpRule
  rdp_listener = [bool]$rdpPort
  winrm_https_firewall_rule_enabled = [bool]$winrmRule
  winrm_https_listener = [bool]$httpsListener
} | ConvertTo-Json -Compress
'@
$guestMessage = az vm run-command invoke --resource-group $ResourceGroup --name $VmName --command-id RunPowerShellScript --scripts $guestScript --query "value[0].message" --output tsv 2>&1
if ($LASTEXITCODE -ne 0 -or -not $guestMessage) { Fail "AZURE_GUEST_INSPECTION_FAILED: Azure Run Command could not inspect the Windows guest." }
$messageText = ($guestMessage | Out-String)
$jsonMatch = [regex]::Match($messageText, '(?s)\{.*\}')
if (-not $jsonMatch.Success) { Fail "GUEST_EVIDENCE_PARSE_FAILED: Windows guest inspection returned no structured evidence." }
try { $guest = $jsonMatch.Value | ConvertFrom-Json } catch { Fail "GUEST_EVIDENCE_PARSE_FAILED: Windows guest JSON was invalid." }
if ([string]$guest.os -notmatch "Windows Server 2025" -or [string]$guest.architecture -notmatch "64") {
    Fail "GUEST_OS_MISMATCH: guest evidence does not confirm 64-bit Windows Server 2025."
}
if (-not $guest.rdp_enabled -or -not $guest.termservice_running -or -not $guest.rdp_firewall_rule_enabled -or -not $guest.rdp_listener) {
    Fail "RDP_GUEST_NOT_READY: guest evidence shows Remote Desktop is not fully enabled/listening."
}
if (-not $guest.winrm_https_firewall_rule_enabled -or -not $guest.winrm_https_listener) {
    Fail "WINRM_GUEST_NOT_READY: guest evidence shows HTTPS WinRM is not fully configured."
}
[ordered]@{
    verified_at_utc = [DateTime]::UtcNow.ToString("o")
    vm_id = $vm.id
    vm_name = $vm.name
    resource_group = $vm.resourceGroup
    location = $vm.location
    provisioning_state = $vm.provisioningState
    power_state = $vm.powerState
    public_ip = $ip
    nsg_rdp_tcp_3389_restricted = $true
    nsg_winrm_tcp_5986_restricted = $true
    guest = $guest
    result = "GUEST_RDP_READY_CLIENT_TEST_REQUIRED"
    note = "Guest and Azure network policy are verified. A successful interactive RDP sign-in from ASUS/Arkan must be tested from that client; this hosted runner cannot prove that client path."
} | ConvertTo-Json -Depth 8

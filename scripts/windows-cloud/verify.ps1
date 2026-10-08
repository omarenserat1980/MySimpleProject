[CmdletBinding()]
param(
    [string]$ResourceGroup = "brain-windows-rg",
    [string]$VmName = "brain-windows-2025",
    [int]$TimeoutSeconds = 600,
    [switch]$SkipAuthenticatedWinRM
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
if ([string]$vm.powerState -ne "VM running") { Fail "VM_NOT_RUNNING: Azure reports '$($vm.powerState)'." }
$ip = [string]$vm.publicIps
if (-not $ip) { Fail "NO_PUBLIC_IP: VM is running but has no public IP to test." }
$tcp = Test-NetConnection -ComputerName $ip -Port 5986 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $tcp) { Fail "WINRM_TCP_FAILED: $($ip):5986 is unreachable. Check NSG, guest firewall, listener and allowed source IP." }
$guest = $null
if (-not $SkipAuthenticatedWinRM) {
    $user = $env:BRAIN_ADMIN_USERNAME
    $password = $env:BRAIN_ADMIN_PASSWORD
    if (-not $user -or -not $password) { Fail "WINRM_AUTH_NOT_TESTED: supply BRAIN_ADMIN_USERNAME and BRAIN_ADMIN_PASSWORD securely." }
    $secure = ConvertTo-SecureString $password -AsPlainText -Force
    $credential = [pscredential]::new($user,$secure)
    $session = $null
    try {
        $options = New-PSSessionOption -SkipCACheck -SkipCNCheck -OperationTimeout 30000
        $session = New-PSSession -ComputerName $ip -Port 5986 -UseSSL -Authentication Negotiate -Credential $credential -SessionOption $options -ErrorAction Stop
        $guest = Invoke-Command -Session $session -ScriptBlock {
            $os = Get-CimInstance Win32_OperatingSystem
            [pscustomobject]@{ computer=$env:COMPUTERNAME; os=$os.Caption; lastBoot=$os.LastBootUpTime.ToString("o") }
        } -ErrorAction Stop
    } catch { Fail "WINRM_AUTH_FAILED: TCP is reachable but authenticated remote command failed. $($_.Exception.Message)" }
    finally { if ($session) { Remove-PSSession $session -ErrorAction SilentlyContinue } }
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
    winrm_tcp_5986 = [bool]$tcp
    authenticated_winrm = [bool](-not $SkipAuthenticatedWinRM)
    guest = $guest
    result = if ($SkipAuthenticatedWinRM) { "PARTIAL_TCP_ONLY" } else { "PASS" }
} | ConvertTo-Json -Depth 8

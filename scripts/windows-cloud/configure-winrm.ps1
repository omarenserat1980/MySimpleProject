[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$AllowedSourceIp)
$ErrorActionPreference = "Stop"
if ($AllowedSourceIp -notmatch '^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$' -or $AllowedSourceIp -eq "0.0.0.0/0") {
    throw "AllowedSourceIp must be a trusted IPv4 CIDR; public-wide access is forbidden."
}
Enable-PSRemoting -Force -SkipNetworkProfileCheck
$cert = New-SelfSignedCertificate -DnsName $env:COMPUTERNAME -CertStoreLocation Cert:\LocalMachine\My -KeyAlgorithm RSA -KeyLength 2048 -NotAfter (Get-Date).AddYears(2)
$httpsListeners = Get-ChildItem WSMan:\Localhost\Listener | Where-Object {
    try { (Get-Item "$($_.PSPath)\Transport" -ErrorAction Stop).Value -eq "HTTPS" } catch { $false }
}
foreach ($listener in $httpsListeners) { Remove-Item -Path $listener.PSPath -Recurse -Force }
New-Item -Path WSMan:\Localhost\Listener -Transport HTTPS -Address * -CertificateThumbPrint $cert.Thumbprint -Force | Out-Null
Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value $false
Set-Item WSMan:\localhost\Service\Auth\Basic -Value $false
Get-NetFirewallRule -DisplayName "Electronic Brain WinRM HTTPS" -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName "Electronic Brain WinRM HTTPS" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 5986 -RemoteAddress $AllowedSourceIp -Profile Any | Out-Null
Restart-Service WinRM
[pscustomobject]@{
    computer = $env:COMPUTERNAME
    winrm_https_listener = [bool](Get-ChildItem WSMan:\Localhost\Listener | Where-Object {
        try { (Get-Item "$($_.PSPath)\Transport" -ErrorAction Stop).Value -eq "HTTPS" } catch { $false }
    })
    firewall_rule = "Electronic Brain WinRM HTTPS"
    allowed_source = $AllowedSourceIp
    certificate_thumbprint = $cert.Thumbprint
} | ConvertTo-Json -Compress

# Read-only diagnostics for the Brain Windows Server 2025 executor host.
# Run in elevated PowerShell on Arkan. This script does not start, stop, or modify VMs/services.
$ErrorActionPreference = "Continue"
$results = [ordered]@{
  schema = "brain.arkan-preflight.v1"
  collected_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  hostname = $env:COMPUTERNAME
  os = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber)
  memory = $null
  hyperv = [ordered]@{ module_available = $false; vm_list_available = $false; vms = @() }
  runner_services = @()
  wsl = [ordered]@{ available = $false; distros = @(); linux_checks = $null }
  findings = @()
}
try {
  $cs = Get-CimInstance Win32_ComputerSystem
  $os = Get-CimInstance Win32_OperatingSystem
  $results.memory = [ordered]@{
    total_bytes = [int64]$cs.TotalPhysicalMemory
    free_bytes = [int64]$os.FreePhysicalMemory * 1024
    total_gib = [math]::Round($cs.TotalPhysicalMemory / 1GB, 2)
    free_gib = [math]::Round(([int64]$os.FreePhysicalMemory * 1024) / 1GB, 2)
  }
} catch { $results.findings += "HOST_MEMORY_QUERY_FAILED" }

try {
  Import-Module Hyper-V -ErrorAction Stop
  $results.hyperv.module_available = $true
  $vms = @(Get-VM -ErrorAction Stop | Select-Object Name, State, Status, Generation, CPUUsage, MemoryAssigned, MemoryStartup, Uptime)
  $results.hyperv.vm_list_available = $true
  $results.hyperv.vms = $vms
  if (-not ($vms | Where-Object Name -eq "Brain-WindowsServer2025")) {
    $results.findings += "BRAIN_WINDOWS_SERVER_2025_VM_NOT_FOUND_IN_HYPERV"
  }
} catch { $results.findings += "HYPERV_MODULE_OR_VM_QUERY_UNAVAILABLE" }

try {
  $results.runner_services = @(Get-Service -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "actions.runner*" -or $_.DisplayName -like "*GitHub Actions Runner*" } |
    Select-Object Name, DisplayName, Status, StartType)
  if (-not $results.runner_services -or -not ($results.runner_services | Where-Object Status -eq "Running")) {
    $results.findings += "NO_RUNNING_GITHUB_ACTIONS_RUNNER_SERVICE_FOUND_ON_WINDOWS_HOST"
  }
} catch { $results.findings += "RUNNER_SERVICE_QUERY_FAILED" }

try {
  $wslExe = Get-Command wsl.exe -ErrorAction Stop
  $distroText = (& $wslExe.Source --list --verbose 2>&1 | Out-String)
  $results.wsl.available = $true
  $results.wsl.distros = @($distroText -split "\r?\n" | Where-Object { $_.Trim() })
  $linuxScript = @'
set +e
printf "linux_arch="; uname -m
printf "qemu="; command -v qemu-system-x86_64 || true
printf "qemu_img="; command -v qemu-img || true
printf "xorriso="; command -v xorriso || true
printf "wimlib="; command -v wimlib-imagex || true
printf "mkfs_vfat="; command -v mkfs.vfat || true
printf "mcopy="; command -v mcopy || true
printf "dev_kvm="; if [ -c /dev/kvm ] && [ -r /dev/kvm ] && [ -w /dev/kvm ]; then echo usable; else echo unavailable; fi
printf "ovmf_code="; test -e /usr/share/OVMF/OVMF_CODE_4M.fd && echo present || echo missing
printf "ovmf_vars="; test -e /usr/share/OVMF/OVMF_VARS_4M.fd && echo present || echo missing
'@
  $linuxResult = (& $wslExe.Source -e bash -lc $linuxScript 2>&1 | Out-String)
  $results.wsl.linux_checks = $linuxResult.Trim()
  if ($linuxResult -notmatch "linux_arch=x86_64") { $results.findings += "WSL_LINUX_ARCH_NOT_X86_64_OR_WSL_CHECK_FAILED" }
  if ($linuxResult -notmatch "dev_kvm=usable") { $results.findings += "WSL_KVM_UNAVAILABLE" }
  foreach ($tool in @("qemu=", "qemu_img=", "xorriso=", "wimlib=", "mkfs_vfat=", "mcopy=")) {
    if ($linuxResult -notmatch [regex]::Escape($tool) -or $linuxResult -match "(?m)^$([regex]::Escape($tool))\s*$") {
      $results.findings += ("WSL_TOOL_MISSING_OR_UNVERIFIED:" + $tool.TrimEnd("="))
    }
  }
} catch { $results.findings += "WSL_UNAVAILABLE_OR_LINUX_DIAGNOSTICS_FAILED" }

if ($results.memory -and $results.memory.free_gib -lt 1.5) {
  $results.findings += "LOW_FREE_HOST_MEMORY_BELOW_1_5_GIB"
}
if (-not $results.findings -or $results.findings.Count -eq 0) {
  $results.findings = @("PREFLIGHT_CHECKS_FOUND_NO_BLOCKERS")
}
$results | ConvertTo-Json -Depth 8

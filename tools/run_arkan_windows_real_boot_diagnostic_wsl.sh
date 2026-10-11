#!/usr/bin/env bash
# Electronic Brain — run Arkan Windows diagnostic from WSL.
# Downloads the reviewed read-only PowerShell diagnostic, then invokes Windows PowerShell.
# No Hyper-V, VM, disk, service, runner, or secret settings are changed.
set -Eeuo pipefail

if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "ERROR: powershell.exe is not available. Run this helper inside WSL on Arkan." >&2
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required to retrieve the diagnostic script." >&2
  exit 2
fi

url="https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/refs/heads/tool/windows-real-boot-preflight-20261011/tools/arkan_windows_real_boot_diagnostic.ps1"
if command -v wslpath >/dev/null 2>&1 && [[ -d /mnt/c/Users/Public/Downloads ]]; then
  win_dir='/mnt/c/Users/Public/Downloads'
  ps1="$win_dir/arkan_windows_real_boot_diagnostic.ps1"
else
  echo "ERROR: expected WSL access to C:\\Users\\Public\\Downloads at /mnt/c/Users/Public/Downloads." >&2
  exit 2
fi

curl --fail --location --silent --show-error "$url" --output "$ps1"
if [[ ! -s "$ps1" ]]; then
  echo "ERROR: downloaded diagnostic is empty." >&2
  exit 3
fi

win_ps1="$(wslpath -w "$ps1")"
echo "Running read-only diagnostic through Windows PowerShell..."
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "$win_ps1"

#!/usr/bin/env bash
# Electronic Brain — one-command Arkan diagnostic + local summary from WSL.
# Read-only on Windows: does not modify Hyper-V, VMs, disks, services, runner settings, or secrets.
set -Eeuo pipefail

branch_url="https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/refs/heads/tool/windows-real-boot-preflight-20261011"
if ! command -v powershell.exe >/dev/null 2>&1; then
  echo "ERROR: powershell.exe is not available. Run this helper inside WSL on Arkan." >&2
  exit 2
fi
for tool in curl wslpath python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERROR: required tool missing: $tool" >&2; exit 2; }
done

win_dir='/mnt/c/Users/Public/Downloads'
[[ -d "$win_dir" ]] || { echo "ERROR: WSL cannot access /mnt/c/Users/Public/Downloads" >&2; exit 2; }

ps1="$win_dir/arkan_windows_real_boot_diagnostic.ps1"
summary='/tmp/summarize_arkan_preflight.py'
curl --fail --location --silent --show-error "$branch_url/tools/arkan_windows_real_boot_diagnostic.ps1" --output "$ps1"
curl --fail --location --silent --show-error "$branch_url/tools/summarize_arkan_preflight.py" --output "$summary"
[[ -s "$ps1" && -s "$summary" ]] || { echo "ERROR: downloaded diagnostic or summarizer is empty" >&2; exit 3; }

win_dir_path="$(wslpath -w "$win_dir")"
win_ps1="$(wslpath -w "$ps1")"
# Important: set the Windows working directory before running the PS1 so the report
# is written to C:\Users\Public\Downloads, not to the WSL UNC current directory.
ps_command="& { Set-Location -LiteralPath '$win_dir_path'; & '$win_ps1' }"
echo "Running read-only diagnostic through Windows PowerShell..."
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "$ps_command"

report="$(find "$win_dir" -maxdepth 1 -type f -name 'brain-arkan-preflight-*.json' -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-)"
if [[ -z "$report" ]]; then
  echo "ERROR: no report found in $win_dir; preserve the PowerShell output above for diagnosis." >&2
  exit 4
fi
echo "REPORT_PATH=$report"
echo "Summarizing the latest local report (no upload)..."
python3 "$summary" "$report"

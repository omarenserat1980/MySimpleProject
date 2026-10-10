# Electronic Brain one-line bootstrap for Windows PowerShell.
# The Linux runtime runs inside WSL; this script never pretends native Windows is the Linux runtime.
$ErrorActionPreference = "Stop"
$Wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if (-not $Wsl) {
  Write-Output "BRAIN_ERROR=WSL_REQUIRED_FOR_WINDOWS_RUNTIME"
  Write-Output "Install and initialize WSL with a Linux distribution, then rerun this one-line command."
  exit 20
}
$Command = 'curl -fsSL https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main/brain_v12/tools/brain-one.sh | bash -s -- activate'
& wsl.exe --exec bash -lc $Command
if ($LASTEXITCODE -ne 0) {
  Write-Output "BRAIN_ERROR=WSL_BOOTSTRAP_FAILED exit_code=$LASTEXITCODE"
  exit $LASTEXITCODE
}

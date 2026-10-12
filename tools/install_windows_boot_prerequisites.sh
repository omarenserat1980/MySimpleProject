#!/usr/bin/env bash
set -euo pipefail

# Installs host packages only after an explicit operator opt-in.
# Does not provision cloud resources, create credentials, configure approvals,
# register a GitHub runner, or start a VM.
if [[ "${BRAIN_ALLOW_SYSTEM_PACKAGE_INSTALL:-}" != "1" ]]; then
  echo "PACKAGE_INSTALL_NOT_AUTHORIZED"
  echo "Review this script, then rerun with BRAIN_ALLOW_SYSTEM_PACKAGE_INSTALL=1 to install OS packages."
  exit 20
fi

[[ "$(id -u)" -ne 0 ]] || { echo "RUN_AS_UNPRIVILEGED_OPERATOR_WITH_SUDO"; exit 21; }
[[ -r /etc/os-release ]] || { echo "LINUX_OS_RELEASE_REQUIRED"; exit 22; }
# shellcheck disable=SC1091
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) echo "UNSUPPORTED_OS_FAMILY:${ID:-unknown}; expected Ubuntu/Debian"; exit 23 ;;
esac
command -v sudo >/dev/null || { echo "SUDO_REQUIRED"; exit 24; }
sudo -v

packages=(
  ca-certificates curl git jq python3 python3-venv
  qemu-system-x86 qemu-utils ovmf xorriso wimtools dosfstools mtools
)
sudo apt-get update
sudo apt-get install -y --no-install-recommends "${packages[@]}"

echo "=== Installed tool checks ==="
for tool in qemu-system-x86_64 qemu-img xorriso wimlib-imagex mkfs.vfat mcopy python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf 'AVAILABLE=%s PATH=%s\n' "$tool" "$(command -v "$tool")"
  else
    printf 'MISSING=%s\n' "$tool"
  fi
done

if [[ -r /dev/kvm && -w /dev/kvm ]]; then
  echo "KVM_DEVICE=READ_WRITE"
else
  echo "KVM_DEVICE=NOT_READY"
  echo "Packages are installed, but real accelerated boot is blocked until the cloud host exposes usable /dev/kvm."
fi

ovmf_found=0
for firmware in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/ovmf/OVMF_CODE.fd; do
  if [[ -f "$firmware" ]]; then
    echo "OVMF_FIRMWARE=$firmware"
    ovmf_found=1
  fi
done
[[ "$ovmf_found" -eq 1 ]] || echo "OVMF_FIRMWARE=NOT_FOUND"

echo "HOST_PACKAGE_SETUP=COMPLETED"
echo "CLOUD_EXECUTOR_ATTESTATION_AND_SIGNED_CONTRACT=NOT_CONFIGURED_BY_THIS_SCRIPT"

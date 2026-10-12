#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare the Linux/WSL substrate required by Electronic Brain's internal runner.
# Default mode is read-only. Pass --install to install apt packages.
INSTALL=0
case "${1:-}" in
  "") ;;
  --install) INSTALL=1 ;;
  -h|--help)
    printf 'Usage: %s [--install]\n' "$0"
    printf 'Default: inspect only. --install: apt update/install required tools.\n'
    exit 0
    ;;
  *)
    printf 'ERROR: unknown argument: %s\n' "$1" >&2
    printf 'Usage: %s [--install]\n' "$0" >&2
    exit 2
    ;;
esac

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "FAIL: this script must run inside Linux/WSL, not Windows PowerShell or Termux."
  exit 2
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "x86_64" && "$ARCH" != "amd64" ]]; then
  echo "FAIL: unsupported architecture: $ARCH (required x86_64/amd64)."
  exit 2
fi

PACKAGES=(
  qemu-system-x86
  qemu-utils
  xorriso
  wimtools
  dosfstools
  mtools
  ffmpeg
  python3
  python3-pip
  python3-venv
  git
  curl
)

if [[ "$INSTALL" == "1" ]]; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "FAIL: apt-get is unavailable; use a supported Ubuntu/Debian WSL distribution."
    exit 2
  fi
  echo "Installing required system packages..."
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends "${PACKAGES[@]}"
fi

REQUIRED_BINS=(
  qemu-system-x86_64
  qemu-img
  xorriso
  wimlib-imagex
  mkfs.vfat
  mcopy
  ffmpeg
  python3
  git
  curl
)

FAILED=0
echo "=== Brain internal runner substrate ==="
printf 'OS: %s\n' "$(. /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-Linux}")"
printf 'Architecture: %s\n' "$ARCH"
printf 'Python: '
python3 --version 2>/dev/null || true
printf 'BRAIN_INTERNAL_RUNNER_FLAG: %s\n' "${BRAIN_INTERNAL_RUNNER_FLAG:+present (value hidden)}"
if [[ "${BRAIN_INTERNAL_RUNNER_FLAG:-}" != "1" ]]; then
  echo "NOTE: runner flag is not set in this shell; do not fake it in the workflow."
fi

for bin in "${REQUIRED_BINS[@]}"; do
  if command -v "$bin" >/dev/null 2>&1; then
    printf 'OK      %s -> %s\n' "$bin" "$(command -v "$bin")"
  else
    printf 'MISSING %s\n' "$bin"
    FAILED=1
  fi
done

if [[ "$FAILED" == "1" ]]; then
  echo "RESULT: NOT_READY"
  if [[ "$INSTALL" == "0" ]]; then
    echo "If this is an Ubuntu/Debian WSL distribution, rerun with --install to install missing packages."
  fi
  exit 1
fi

echo "RESULT: TOOLS_READY"
echo "This proves only OS/tool availability, not GitHub runner registration or Brain API health."

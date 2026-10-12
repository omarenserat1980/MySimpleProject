#!/usr/bin/env bash
# Safe preflight for the Electronic Brain Windows 95 QEMU appliance.
# Read-only checks only: does not install packages, create cloud resources, or start a VM.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${WIN95_ISO_PATH:-$ROOT/media/windows95.iso}"
DATA_DIR="${WIN95_DATA_DIR:-$ROOT/data}"
DISK="${WIN95_DISK_PATH:-$DATA_DIR/windows95.qcow2}"
fail=0

ok()   { printf 'PASS  %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }
bad()  { printf 'FAIL  %s\n' "$*"; fail=1; }

printf '%s\n' 'Electronic Brain — Windows 95 VM preflight' 'This check does not start the VM or provision cloud resources.' ''

if command -v docker >/dev/null 2>&1; then
  ok "Docker executable found: $(command -v docker)"
  if docker info >/dev/null 2>&1; then ok 'Docker daemon reachable'; else warn 'Docker daemon not reachable for this user'; fi
else
  bad 'Docker is not installed'
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  ok 'Docker Compose plugin available'
else
  warn 'Docker Compose plugin unavailable'
fi

if command -v qemu-system-i386 >/dev/null 2>&1 || command -v qemu-system-x86_64 >/dev/null 2>&1; then
  ok 'QEMU x86 system emulator found on host'
else
  warn 'QEMU not installed on host (container image installs it at build time)'
fi

if [ -f "$ISO" ] && [ -s "$ISO" ]; then
  ok "Non-empty installation ISO found: $ISO"
else
  bad "Licensed Windows 95 ISO missing or empty: $ISO"
fi

if [ -d "$DATA_DIR" ] && [ -w "$DATA_DIR" ]; then
  ok "Persistent data directory writable: $DATA_DIR"
elif [ -d "$(dirname "$DATA_DIR")" ] && [ -w "$(dirname "$DATA_DIR")" ]; then
  ok "Parent directory writable; data directory can be created later: $DATA_DIR"
else
  bad "Persistent data directory parent is not writable: $DATA_DIR"
fi

if [ -e "$DISK" ]; then
  if [ -s "$DISK" ]; then ok "Existing virtual disk found: $DISK"; else bad "Virtual disk exists but is empty: $DISK"; fi
else
  warn "Virtual disk not created yet (expected before first start): $DISK"
fi

if command -v df >/dev/null 2>&1; then
  df -Pk "$(dirname "$DATA_DIR")" 2>/dev/null | awk 'NR==2 {printf "INFO  Free space at data path: %.2f GiB\n", $4/1024/1024}'
fi

printf '\n'
if [ "$fail" -eq 0 ]; then
  printf '%s\n' 'PREFLIGHT=PASS_WITH_WARNINGS_POSSIBLE' 'BOOT_STATUS=NOT_BOOT_VERIFIED'
  exit 0
else
  printf '%s\n' 'PREFLIGHT=BLOCKED' 'BOOT_STATUS=NOT_BOOT_VERIFIED'
  exit 1
fi

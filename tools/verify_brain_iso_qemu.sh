#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/Users/Administrator/Documents/GitHub/MySimpleProject
ISO=brain-boot-self-trust.iso
LOG=brain-iso-serial.log
rm -f "$LOG" /tmp/brain-qemu.log
set +e
timeout 12s qemu-system-x86_64 -machine q35 -m 128M -cdrom "$ISO" -display none -serial file:"$LOG" >/tmp/brain-qemu.log 2>&1
rc=$?
set -e
cat "$LOG" 2>/dev/null || true
if grep -q 'BRAIN-BOOT-1 SELF-TRUST BOOTSTRAP' "$LOG"; then
  echo 'BRAIN_BOOT_ISO_QEMU=VERIFIED'
  exit 0
fi
cat /tmp/brain-qemu.log 2>/dev/null || true
echo "BRAIN_BOOT_ISO_QEMU=NOT_VERIFIED rc=$rc"
exit 1

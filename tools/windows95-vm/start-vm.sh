#!/bin/sh
set -eu

RAM_MB="${WIN95_RAM_MB:-128}"
DISK_GB="${WIN95_DISK_GB:-2}"
ISO_PATH="${WIN95_ISO_PATH:-/media/windows95.iso}"
DISK_PATH="${WIN95_DISK_PATH:-/data/windows95.qcow2}"
BOOT_MODE="${WIN95_BOOT_MODE:-cd}"

case "$RAM_MB" in *[!0-9]*|"") echo "WIN95_RAM_MB must be numeric" >&2; exit 2;; esac
case "$DISK_GB" in *[!0-9]*|"") echo "WIN95_DISK_GB must be numeric" >&2; exit 2;; esac
[ "$RAM_MB" -ge 64 ] && [ "$RAM_MB" -le 512 ] || { echo "RAM must be 64..512 MiB" >&2; exit 2; }
[ "$DISK_GB" -ge 1 ] && [ "$DISK_GB" -le 8 ] || { echo "Disk must be 1..8 GiB" >&2; exit 2; }

case "$BOOT_MODE" in
  cd)
    [ -f "$ISO_PATH" ] && [ -s "$ISO_PATH" ] && [ -r "$ISO_PATH" ] || {
      echo "Windows 95 installation ISO must exist, be non-empty, and readable at $ISO_PATH. Supply media you are licensed to use." >&2
      exit 3
    }
    ;;
  disk) ;;
  *) echo "WIN95_BOOT_MODE must be cd or disk" >&2; exit 2;;
esac

mkdir -p "$(dirname "$DISK_PATH")"
if [ ! -e "$DISK_PATH" ]; then
  qemu-img create -f qcow2 "$DISK_PATH" "${DISK_GB}G"
fi
[ -s "$DISK_PATH" ] || { echo "Virtual disk is empty: $DISK_PATH" >&2; exit 4; }

# QEMU is software-emulated; no KVM or privileged container is required.
# VNC is kept on loopback. noVNC must remain behind authenticated HTTPS/tunnel
# when accessed remotely; do not expose the raw port to the public internet.
set -- qemu-system-i386 \
  -machine pc,accel=tcg \
  -cpu pentium \
  -m "$RAM_MB" \
  -vga cirrus \
  -rtc base=localtime \
  -drive "file=$DISK_PATH,format=qcow2,if=ide"

if [ "$BOOT_MODE" = cd ]; then
  set -- "$@" -cdrom "$ISO_PATH" -boot order=d
else
  set -- "$@" -boot order=c
fi

"$@" -vnc 127.0.0.1:0 -no-reboot &
QEMU_PID=$!
cleanup() {
  kill "$QEMU_PID" 2>/dev/null || true
  wait "$QEMU_PID" 2>/dev/null || true
  if [ "${WEB_PID:-}" ]; then kill "$WEB_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 &
WEB_PID=$!
wait "$QEMU_PID"

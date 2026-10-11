#!/bin/sh
set -eu

RAM_MB="${WIN95_RAM_MB:-128}"
DISK_GB="${WIN95_DISK_GB:-2}"
ISO_PATH="${WIN95_ISO_PATH:-/media/windows95.iso}"
DISK_PATH="${WIN95_DISK_PATH:-/data/windows95.qcow2}"

case "$RAM_MB" in *[!0-9]*|"") echo "WIN95_RAM_MB must be numeric" >&2; exit 2;; esac
case "$DISK_GB" in *[!0-9]*|"") echo "WIN95_DISK_GB must be numeric" >&2; exit 2;; esac
[ "$RAM_MB" -ge 64 ] && [ "$RAM_MB" -le 512 ] || { echo "RAM must be 64..512 MiB" >&2; exit 2; }
[ "$DISK_GB" -ge 1 ] && [ "$DISK_GB" -le 8 ] || { echo "Disk must be 1..8 GiB" >&2; exit 2; }
[ -r "$ISO_PATH" ] || { echo "Windows 95 installation ISO not found/readable at $ISO_PATH. Supply media you are licensed to use." >&2; exit 3; }

mkdir -p "$(dirname "$DISK_PATH")"
if [ ! -e "$DISK_PATH" ]; then
  qemu-img create -f qcow2 "$DISK_PATH" "${DISK_GB}G"
fi

# QEMU is software-emulated; no KVM or privileged container is required.
# VNC is kept on loopback. noVNC is only bound to the container interface;
# compose binds the host port to 127.0.0.1 by default.
qemu-system-i386 \
  -machine pc,accel=tcg \
  -cpu pentium \
  -m "$RAM_MB" \
  -vga cirrus \
  -rtc base=localtime \
  -drive "file=$DISK_PATH,format=qcow2,if=ide" \
  -cdrom "$ISO_PATH" \
  -boot order=d \
  -vnc 127.0.0.1:0 \
  -no-reboot &
QEMU_PID=$!
cleanup() { kill "$QEMU_PID" 2>/dev/null || true; wait "$QEMU_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Serve noVNC's browser client. Do not expose this endpoint publicly without
# authentication and TLS at a trusted reverse proxy.
websockify --web=/usr/share/novnc 6080 127.0.0.1:5900 &
WEB_PID=$!
wait "$QEMU_PID"
kill "$WEB_PID" 2>/dev/null || true

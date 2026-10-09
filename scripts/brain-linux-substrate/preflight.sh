#!/usr/bin/env bash
set -euo pipefail

# Brain Linux Execution Substrate gate.
# This is deliberately fail-closed: it never installs packages, changes
# virtualization settings, or creates cloud resources.
#
# Success means the host is genuinely capable of running the Brain-owned
# Linux/KVM execution layer required by cloud_executor_gate.py.

fail() { echo "BRAIN_LINUX_SUBSTRATE=BLOCKED:$*" >&2; exit 2; }

[ "$(uname -s)" = "Linux" ] || fail "HOST_OS_NOT_LINUX:$(uname -s)"
case "$(uname -m)" in
  x86_64|amd64) ;;
  *) fail "HOST_ARCH_NOT_X64:$(uname -m)" ;;
esac

[ -r /dev/kvm ] && [ -w /dev/kvm ] || fail "KVM_DEVICE_UNAVAILABLE:/dev/kvm"

for tool in qemu-system-x86_64 qemu-img xorriso wimlib-imagex mkfs.vfat mcopy; do
  command -v "$tool" >/dev/null 2>&1 || fail "REQUIRED_TOOL_MISSING:$tool"
done

qemu="$(command -v qemu-system-x86_64)"
"$qemu" -accel help 2>&1 | grep -qi kvm || fail "QEMU_KVM_ACCEL_UNAVAILABLE"

set +e
timeout 5 "$qemu" -accel kvm -machine q35 -nodefaults -display none -S >/tmp/brain-kvm-probe.log 2>&1
rc=$?
set -e
if [ "$rc" -ne 124 ]; then
  echo "=== KVM PROBE ===" >&2
  cat /tmp/brain-kvm-probe.log >&2 || true
  fail "KVM_RUNTIME_PROBE_FAILED:exit=$rc"
fi

echo "BRAIN_LINUX_SUBSTRATE=VERIFIED"
echo "BRAIN_LINUX_SUBSTRATE_OS=$(uname -s)"
echo "BRAIN_LINUX_SUBSTRATE_ARCH=$(uname -m)"
echo "BRAIN_LINUX_SUBSTRATE_KVM=/dev/kvm"
echo "BRAIN_LINUX_SUBSTRATE_QEMU=$qemu"

#!/usr/bin/env bash
# Read-only diagnostic for the dedicated Linux QEMU/KVM runner.
# Does not issue contracts, consume approvals, download media, modify disks, or start VMs.
set -uo pipefail
report="${1:-windows-real-boot-runner-diagnostic.txt}"
: > "$report"
failures=0
ok(){ printf 'PASS %s\n' "$1" | tee -a "$report"; }
block(){ printf 'BLOCK %s\n' "$1" | tee -a "$report"; failures=$((failures+1)); }

printf 'diagnostic=windows-real-boot-runner\n' | tee -a "$report"
printf 'timestamp_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$report"
[[ "$(uname -s)" == Linux ]] && ok "os_linux" || block "os_linux_required"
[[ "$(uname -m)" == x86_64 ]] && ok "arch_x86_64" || block "arch_x86_64_required"
[[ "${BRAIN_INTERNAL_RUNNER_FLAG:-}" == 1 ]] && ok "brain_internal_runner_flag" || block "brain_internal_runner_flag_missing"

for tool in qemu-system-x86_64 qemu-img xorriso wimlib-imagex mcopy; do
  command -v "$tool" >/dev/null 2>&1 && ok "tool_present:$tool" || block "tool_missing:$tool"
done
if command -v mkfs.vfat >/dev/null 2>&1 || command -v mkfs.fat >/dev/null 2>&1; then
  ok "tool_present:fat_formatter"
else
  block "tool_missing:fat_formatter"
fi
ovmf=""
for candidate in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/ovmf/OVMF_CODE_4M.fd /usr/share/edk2/ovmf/OVMF_CODE.fd; do
  if [[ -r "$candidate" ]]; then ovmf="$candidate"; break; fi
done
[[ -n "$ovmf" ]] && ok "ovmf_readable" || block "ovmf_missing"
[[ -r /dev/kvm && -w /dev/kvm ]] && ok "kvm_read_write" || block "kvm_missing_or_not_read_write"

for name in \
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED \
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED \
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED \
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED \
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED; do
  [[ -n "${!name:-}" ]] && ok "protected_input_present:$name" || block "protected_input_missing:$name"
done

printf 'failures=%d\n' "$failures" | tee -a "$report"
printf 'contract_issued=false\nboot_verified=false\nsystem_state_changed=false\n' | tee -a "$report"
if (( failures )); then
  printf 'result=BLOCKED_NO_SIDE_EFFECTS\n' | tee -a "$report"
  exit 2
fi
printf 'result=RUNNER_READY_FOR_CONTRACT_GATE_ONLY\n' | tee -a "$report"

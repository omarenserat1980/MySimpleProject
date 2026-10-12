#!/usr/bin/env bash
# Read-only preflight for the Electronic Brain Windows Server 2025 real-boot runner.
# This script NEVER downloads an ISO, creates/changes disks, starts QEMU, or prints secret values.
set -uo pipefail

failures=0
warnings=0
ok()   { printf 'PASS  %s\n' "$1"; }
fail() { printf 'BLOCK %s\n' "$1"; failures=$((failures + 1)); }
warn() { printf 'WARN  %s\n' "$1"; warnings=$((warnings + 1)); }

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then ok "tool:$1"; else fail "missing_tool:$1"; fi
}

printf '%s\n' 'Electronic Brain — Windows Server 2025 real-boot preflight (read-only)'
printf 'timestamp_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)"

if [[ "$(uname -s 2>/dev/null || true)" == Linux ]]; then
  ok 'os:Linux'
else
  fail 'os:Linux_required'
fi
if [[ "$(uname -m 2>/dev/null || true)" == x86_64 ]]; then
  ok 'arch:x86_64'
else
  fail 'arch:x86_64_required'
fi

for cmd in qemu-system-x86_64 qemu-img xorriso wimlib-imagex; do check_cmd "$cmd"; done
if command -v mkfs.vfat >/dev/null 2>&1; then
  ok 'tool:mkfs.vfat'
elif command -v mkfs.fat >/dev/null 2>&1; then
  ok 'tool:mkfs.fat'
else
  fail 'missing_tool:mkfs.vfat_or_mkfs.fat'
fi
check_cmd mcopy

ovmf=''
for candidate in \
  /usr/share/OVMF/OVMF_CODE_4M.fd \
  /usr/share/OVMF/OVMF_CODE.fd \
  /usr/share/edk2/ovmf/OVMF_CODE_4M.fd \
  /usr/share/edk2/ovmf/OVMF_CODE.fd; do
  if [[ -r "$candidate" ]]; then ovmf="$candidate"; break; fi
done
if [[ -n "$ovmf" ]]; then ok 'firmware:OVMF_readable'; else fail 'missing_firmware:OVMF_CODE'; fi

if [[ -e /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
  ok 'kvm:/dev/kvm_read_write'
else
  fail 'kvm:/dev/kvm_missing_or_not_read_write'
fi

if [[ "${BRAIN_INTERNAL_RUNNER_FLAG:-}" == 1 ]]; then
  ok 'runner:BRAIN_INTERNAL_RUNNER_FLAG'
else
  fail 'runner:BRAIN_INTERNAL_RUNNER_FLAG_not_1'
fi
if [[ "${RUNNER_OS:-}" == Linux || -z "${RUNNER_OS:-}" ]]; then
  [[ -n "${RUNNER_OS:-}" ]] && ok 'runner:RUNNER_OS_Linux' || warn 'runner:RUNNER_OS_unset_outside_GitHub_Actions'
else
  fail 'runner:RUNNER_OS_not_Linux'
fi
if [[ "${RUNNER_ARCH:-}" == X64 || -z "${RUNNER_ARCH:-}" ]]; then
  [[ -n "${RUNNER_ARCH:-}" ]] && ok 'runner:RUNNER_ARCH_X64' || warn 'runner:RUNNER_ARCH_unset_outside_GitHub_Actions'
else
  fail 'runner:RUNNER_ARCH_not_X64'
fi

# These variables must be explicitly mapped from the protected GitHub Environment.
# Values are never printed; only presence is reported.
required_vars=(
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
)
for name in "${required_vars[@]}"; do
  if [[ -n "${!name:-}" ]]; then ok "protected_input_present:$name"; else fail "protected_input_missing:$name"; fi
done

contract="${BRAIN_WINDOWS_EXECUTION_CONTRACT_FILE:-}"
if [[ -n "$contract" && -f "$contract" && -r "$contract" ]]; then
  ok 'contract:file_present_readable'
  # Never print the contract path or contents; report only safe metadata.
  if [[ -s "$contract" ]]; then ok 'contract:file_nonempty'; else fail 'contract:file_empty'; fi
else
  fail 'contract:WINDOWS_EXECUTION_CONTRACT_FILE_REQUIRED'
fi

printf 'summary=failures:%d,warnings:%d\n' "$failures" "$warnings"
if (( failures > 0 )); then
  printf '%s\n' 'result=NOT_READY_NO_SIDE_EFFECTS_PERFORMED'
  exit 2
fi
printf '%s\n' 'result=PRECHECK_READY_CONTRACT_SIGNATURE_STILL_MUST_BE_VERIFIED_BY_OFFICIAL_GATE'
exit 0

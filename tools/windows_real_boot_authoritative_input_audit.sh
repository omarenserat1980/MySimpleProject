#!/usr/bin/env bash
# Electronic Brain: authoritative-input audit for Windows Server 2025 real boot.
# Safe by default: never prints secret values, creates credentials, issues contracts,
# provisions cloud resources, downloads an ISO, or starts a VM.
set -Eeuo pipefail
umask 077

REPO="${GH_REPO:-omarenserat1980/MySimpleProject}"
ENVIRONMENT="windows-real-boot"
DEFAULT_CONTROL_PLANE_URL="https://brain-control-plane-main.onrender.com"
die() { printf 'BLOCKED: %s\n' "$*" >&2; exit 2; }

command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) is required."
gh auth status >/dev/null 2>&1 || die "Authenticate with gh auth login first."
gh repo view "$REPO" --json nameWithOwner >/dev/null 2>&1 || die "Repository access unavailable."

# The endpoint is configuration, not a credential. Per the secret matrix, it is
# optional because the deployed Free HTTPS Control Plane URL is the safe fallback.
required=(
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
)

printf 'REPOSITORY=%s\nENVIRONMENT=%s\n' "$REPO" "$ENVIRONMENT"
secret_names="$(gh secret list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name')" \
  || die "Cannot list environment secret names; check permissions."
variables_json="$(gh variable list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name' 2>/dev/null || true)"

missing=0
for name in "${required[@]}"; do
  if grep -Fxq "$name" <<< "$secret_names"; then
    printf 'NAME_PRESENT=%s\n' "$name"
  else
    printf 'NAME_MISSING=%s\n' "$name"
    missing=$((missing + 1))
  fi
done

if grep -Fxq "BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED" <<< "$secret_names"; then
  echo "CONTROL_PLANE_ENDPOINT_SOURCE=OPTIONAL_PROTECTED_SECRET_NAME_PRESENT_VALUE_UNVERIFIED"
elif grep -Fxq "BRAIN_WINDOWS_CONTROL_PLANE_URL" <<< "$variables_json"; then
  echo "CONTROL_PLANE_ENDPOINT_SOURCE=OPTIONAL_ENVIRONMENT_VARIABLE_NAME_PRESENT_VALUE_UNVERIFIED"
else
  echo "CONTROL_PLANE_ENDPOINT_SOURCE=DOCUMENTED_FREE_HTTPS_FALLBACK"
  echo "CONTROL_PLANE_ENDPOINT_DEFAULT=$DEFAULT_CONTROL_PLANE_URL"
fi

printf 'MISSING_REQUIRED_SECRET_NAME_COUNT=%d\n' "$missing"
printf '%s\n' 'SECRET_VALUES=NOT_READABLE_BY_NAME_AUDIT'
printf '%s\n' 'SECRET_VALUE_VALIDITY=NOT_VERIFIED_BY_NAME_CHECK'

issue_state="$(gh issue view 225 --repo "$REPO" --json state --jq '.state' 2>/dev/null || printf 'UNKNOWN')"
printf 'CONTRACT_BLOCKER_ISSUE_225_STATE=%s\n' "$issue_state"

if (( missing > 0 )); then
  printf '%s\n' 'RESULT=BLOCKED_MISSING_REQUIRED_SECRET_NAMES'
  printf '%s\n' 'ACTION=Obtain authorized values from the executor/Control Plane owner; do not invent placeholders.'
  exit 2
fi

printf '%s\n' 'RESULT=REQUIRED_SECRET_NAMES_PRESENT_VALUES_UNVERIFIED'
printf '%s\n' 'ACTION=Run scripts/github/run_windows_real_boot_readiness.sh only after endpoint reachability, trusted runner, and signed-contract prerequisites are verified.'
printf '%s\n' 'NETWORK_REACHABILITY=NOT_TESTED'
printf '%s\n' 'EXECUTOR_ENROLLMENT=NOT_VERIFIED'
printf '%s\n' 'WINDOWS_SERVER_2025_BOOT=NOT_VERIFIED'

#!/usr/bin/env bash
# Securely stage authorized Windows real-boot secrets into a GitHub Environment.
# Secret values are prompted with echo disabled and piped to gh via stdin.
# This script never generates authority keys, owner approvals, tokens, or contracts.
set -Eeuo pipefail
umask 077

ENVIRONMENT="windows-real-boot"
REPO="${GH_REPO:-omarenserat1980/MySimpleProject}"

die() { printf 'BLOCKED: %s\n' "$*" >&2; exit 2; }
command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) is required."
command -v python3 >/dev/null 2>&1 || die "python3 is required."
gh auth status >/dev/null 2>&1 || die "Authenticate with gh auth login first."
gh repo view "$REPO" --json nameWithOwner >/dev/null 2>&1 || die "Repository access unavailable."
printf 'Repository: %s\nEnvironment: %s\n' "$REPO" "$ENVIRONMENT"
printf '%s\n' 'This tool will not generate or invent trusted credentials.'
printf '%s\n' 'Obtain every value from the authorized Control Plane/executor owner.'
printf '%s\n' 'Values are not echoed or written to disk; each is sent to gh via stdin.'
printf '%s\n' 'Press Ctrl-C to stop. Existing secrets not entered here are not modified.'

names=(
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED
  BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
)

validate() {
  local name="$1" value="$2"
  [[ -n "${value//[[:space:]]/}" ]] || return 1
  case "$value" in
    *PLACEHOLDER*|*REPLACE_ME*|*CHANGEME*|*YOUR_TOKEN*|*example.com*|*localhost*)
      printf 'Rejected placeholder/local value for %s.\n' "$name" >&2; return 1 ;;
  esac
  case "$name" in
    BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED|BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED)
      python3 - "$value" <<'PY'
import sys
from urllib.parse import urlsplit
try:
    u = urlsplit(sys.argv[1].strip())
    ok = u.scheme == "https" and bool(u.hostname) and not u.username and not u.password
except Exception:
    ok = False
raise SystemExit(0 if ok else 1)
PY
      ;;
    BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED|BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED)
      printf '%s' "$value" | python3 -c 'import base64,sys; s=sys.stdin.read().strip(); b=base64.b64decode(s,validate=True); sys.exit(0 if len(b)>=32 else 1)' ;;
    BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED|BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED)
      [[ ${#value} -ge 32 ]] ;;
    *) return 1 ;;
  esac
}

for name in "${names[@]}"; do
  printf '\n%s\n' "$name"
  printf 'Enter the REAL authorized value (hidden; blank skips): '
  IFS= read -r -s value || exit 130
  printf '\n'
  if [[ -z "$value" ]]; then
    printf 'SKIPPED: %s\n' "$name"
    continue
  fi
  if ! validate "$name" "$value"; then
    unset value
    die "Value validation failed for $name; secret was not changed."
  fi
  # gh reads the secret from stdin; never pass secret material as a CLI argument.
  if printf '%s' "$value" | gh secret set "$name" --repo "$REPO" --env "$ENVIRONMENT"; then
    printf 'STAGED: %s (value not displayed)\n' "$name"
  else
    unset value
    die "GitHub rejected secret write for $name. Check environment permissions."
  fi
  unset value
done

printf '\nSecret names visible to the authenticated CLI (values are never retrievable):\n'
gh secret list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name'
printf '\nNEXT: run the protected Control Plane endpoint diagnostic.\n'
printf 'This tool does not test endpoint reachability, issue a contract, or prove Windows boot.\n'

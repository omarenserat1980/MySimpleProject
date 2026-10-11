#!/usr/bin/env bash
# Securely configure missing Windows real-boot Environment secrets from protected local files.
# Secret values are never printed, embedded in process arguments, or committed.
set -Eeuo pipefail
set +x
umask 077

repo="${GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
environment="windows-real-boot"
overwrite="${BRAIN_ALLOW_SECRET_OVERWRITE:-NO}"

names=(
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
)
declare -A source_files=(
  [BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED]="${BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_FILE:-}"
  [BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED]="${BRAIN_CLOUD_EXECUTOR_TOKEN_FILE:-}"
  [BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED]="${BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_FILE:-}"
  [BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED]="${BRAIN_AUTHORITY_PUBLIC_KEY_B64_FILE:-}"
  [BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED]="${BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_FILE:-}"
)

echo "BRAIN_ENV_SECRET_SETUP=START"
echo "REPOSITORY=$repo"
echo "ENVIRONMENT=$environment"
echo "SECRET_VALUES=NEVER_PRINTED"

command -v gh >/dev/null 2>&1 || { echo "RESULT=BLOCKED_GH_CLI_MISSING"; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "RESULT=BLOCKED_PYTHON3_MISSING"; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "RESULT=BLOCKED_GH_NOT_AUTHENTICATED"; exit 2; }
gh repo view "$repo" --json nameWithOwner >/dev/null 2>&1 || { echo "RESULT=BLOCKED_REPOSITORY_ACCESS"; exit 2; }
gh api "repos/$repo/environments/$environment" >/dev/null 2>&1 || {
  echo "RESULT=BLOCKED_ENVIRONMENT_ACCESS"; exit 2;
}

# Fail closed before changing anything unless every required source is present and owner-only.
for name in "${names[@]}"; do
  file="${source_files[$name]}"
  if [[ -z "$file" || ! -f "$file" || ! -r "$file" || -L "$file" ]]; then
    printf 'RESULT=BLOCKED_INPUT_FILE_REQUIRED:%s\n' "$name"
    exit 2
  fi
  mode="$(stat -c '%a' "$file" 2>/dev/null || stat -f '%Lp' "$file" 2>/dev/null || true)"
  if [[ -z "$mode" ]] || (( (8#$mode & 077) != 0 )); then
    printf 'RESULT=BLOCKED_INPUT_FILE_PERMISSIONS:%s\n' "$name"
    echo "REQUIRED_MODE=OWNER_ONLY (for example chmod 600)"
    exit 2
  fi
done

python3 - "${source_files[BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED]}" \
  "${source_files[BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED]}" \
  "${source_files[BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED]}" \
  "${source_files[BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED]}" \
  "${source_files[BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED]}" <<'PY'
import base64, pathlib, sys
from urllib.parse import urlparse
url, token, attestation_key, authority_key, delivery_key = [
    pathlib.Path(p).read_text(encoding="utf-8").strip() for p in sys.argv[1:]
]
u = urlparse(url)
if u.scheme != "https" or not u.hostname or u.username or u.password or any(c.isspace() for c in url):
    raise SystemExit("RESULT=BLOCKED_REGISTRY_URL_MUST_BE_HTTPS")
if len(token) < 32 or any(c.isspace() for c in token):
    raise SystemExit("RESULT=BLOCKED_EXECUTOR_TOKEN_INVALID")
for label, value in (("ATTESTATION_PUBLIC_KEY", attestation_key), ("AUTHORITY_PUBLIC_KEY", authority_key)):
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception:
        raise SystemExit("RESULT=BLOCKED_"+label+"_NOT_BASE64")
    if len(raw) < 32:
        raise SystemExit("RESULT=BLOCKED_"+label+"_TOO_SHORT")
if len(delivery_key) < 32 or any(c.isspace() for c in delivery_key):
    raise SystemExit("RESULT=BLOCKED_CONTRACT_DELIVERY_KEY_INVALID")
print("INPUT_VALIDATION=PASS")
PY

existing="$(gh secret list --repo "$repo" --env "$environment" --json name --jq '.[].name')" || {
  echo "RESULT=BLOCKED_CANNOT_LIST_ENVIRONMENT_SECRET_NAMES"; exit 2;
}

for name in "${names[@]}"; do
  if grep -Fxq "$name" <<< "$existing" && [[ "$overwrite" != "YES" ]]; then
    printf 'SECRET_ACTION=%s:PRESERVED_ALREADY_EXISTS\n' "$name"
    continue
  fi
  # Trim a normal trailing newline before piping; values never enter argv or logs.
  if python3 -c 'import pathlib,sys; sys.stdout.write(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").strip())' "${source_files[$name]}" | gh secret set "$name" --repo "$repo" --env "$environment" >/dev/null; then
    printf 'SECRET_ACTION=%s:SET_REQUEST_SUCCEEDED\n' "$name"
  else
    printf 'SECRET_ACTION=%s:FAILED\n' "$name"
    echo "RESULT=PARTIAL_OR_FAILED; review secret names and rerun after correcting the cause."
    exit 3
  fi
done

echo "RESULT=SETUP_REQUESTS_COMPLETE"
echo "NOTE=Use only values issued by the trusted Control Plane/authority. This does not enroll an executor, issue a contract, or prove Windows boot."

#!/usr/bin/env bash
# Describe and safely audit the Brain executor-token secret.
# Never reads/prints secret values, creates tokens, or changes configuration.
set -Eeuo pipefail
umask 077

REPO="${GH_REPO:-omarenserat1980/MySimpleProject}"
BRANCH="${BRAIN_AUDIT_SOURCE_REF:-main}"
ENVIRONMENT="windows-real-boot"
SECRET="BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED"
ENROLLMENTS_VAR="BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON"
SOURCE_PATH="brain_v12/brain/cloud_executor_attestation_api.py"
SETUP_PATH="brain_v12/CLOUD_EXECUTOR_CONTROL_PLANE_SETUP.md"
tmpdir=""

cleanup() {
  if [[ -n "$tmpdir" && -d "$tmpdir" ]]; then rm -rf -- "$tmpdir"; fi
}
trap cleanup EXIT

printf '%s\n' "Electronic Brain — Executor Token Secret Audit"
printf 'REPOSITORY=%s\nSOURCE_REF=%s\nENVIRONMENT=%s\nSECRET_NAME=%s\n' "$REPO" "$BRANCH" "$ENVIRONMENT" "$SECRET"
printf '%s\n' \
  'PURPOSE=Per-executor bearer credential used to authenticate to the Brain cloud-executor attestation registry.' \
  'VALIDATION=The Control Plane hashes the supplied token with SHA-256 and compares it with the enrolled executor ID digest.' \
  'SAFE_HANDLING=Generate on a trusted management host; configure only the digest on the Control Plane; deliver the raw token through an approved secret channel.' \
  'GITHUB_LIMIT=GitHub secret values cannot be retrieved after saving; this tool checks names only.' \
  'SAFETY=This tool never generates, retrieves, prints, guesses, or changes any secret value.'

if ! command -v gh >/dev/null 2>&1; then
  echo 'RESULT=BLOCKED_GH_CLI_MISSING'; exit 2
fi
if ! gh auth status >/dev/null 2>&1; then
  echo 'RESULT=BLOCKED_GH_NOT_AUTHENTICATED'; exit 2
fi
if ! gh repo view "$REPO" --json nameWithOwner >/dev/null 2>&1; then
  echo 'RESULT=BLOCKED_REPOSITORY_ACCESS'; exit 2
fi

names="$(gh secret list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name')" || {
  echo 'RESULT=BLOCKED_CANNOT_LIST_ENVIRONMENT_SECRET_NAMES'; exit 2;
}
if grep -Fxq "$SECRET" <<< "$names"; then
  echo 'GITHUB_SECRET_NAME=PRESENT'
  echo 'GITHUB_SECRET_VALUE=UNREADABLE_BY_DESIGN'
else
  echo 'GITHUB_SECRET_NAME=MISSING'
fi

echo
echo 'REQUIRED_ENVIRONMENT_SECRET_NAME_AUDIT_BEGIN'
for required in \
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED \
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED \
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED \
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED \
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED; do
  if grep -Fxq "$required" <<< "$names"; then
    printf 'SECRET_NAME_STATUS=%s:PRESENT\n' "$required"
  else
    printf 'SECRET_NAME_STATUS=%s:MISSING\n' "$required"
  fi
done
echo 'REQUIRED_ENVIRONMENT_SECRET_NAME_AUDIT_END'
echo 'SECRET_VALUES=NEVER_READ_OR_PRINTED'

# Inspect authoritative source files from GitHub, not the user's potentially stale checkout.
tmpdir="$(mktemp -d)"
source_file="$tmpdir/cloud_executor_attestation_api.py"
setup_file="$tmpdir/CLOUD_EXECUTOR_CONTROL_PLANE_SETUP.md"
if gh api "repos/$REPO/contents/$SOURCE_PATH?ref=$BRANCH" --jq '.content' 2>/dev/null | base64 -d > "$source_file" &&
   gh api "repos/$REPO/contents/$SETUP_PATH?ref=$BRANCH" --jq '.content' 2>/dev/null | base64 -d > "$setup_file"; then
  if grep -Fq "$ENROLLMENTS_VAR" "$source_file" && grep -Fq "$ENROLLMENTS_VAR" "$setup_file"; then
    echo 'REMOTE_SOURCE_REFERENCE=FOUND'
    echo "REMOTE_SOURCE_REF=$BRANCH"
  else
    echo 'REMOTE_SOURCE_REFERENCE=NOT_FOUND_OR_CHANGED'
    echo "REMOTE_SOURCE_REF=$BRANCH"
  fi
else
  echo 'REMOTE_SOURCE_REFERENCE=UNAVAILABLE'
  echo 'REASON=Cannot fetch both authoritative source files; check repository access and ref.'
fi

cat <<'NEXT'
NEXT_STEPS:
1. Confirm the authoritative HTTPS Control Plane is deployed with durable nonce storage and the approved executor ID/host binding.
2. Generate a high-entropy per-executor token on the trusted management host; do not put the raw token in source control or chat.
3. Configure only its SHA-256 digest in BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON on the Control Plane.
4. Deliver the raw token through the approved secure channel and save it as the windows-real-boot Environment secret.
5. Verify the challenge/attestation flow succeeds without logging the token, then run the real-boot workflow and inspect same-run guest boot evidence.
Do not use a GitHub personal access token, a placeholder, or an unenrolled token.
This audit checks secret names and source references only. It does not configure the Control Plane, enroll executors, issue contracts, or prove Windows boot.
NEXT

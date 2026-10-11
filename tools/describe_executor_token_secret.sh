#!/usr/bin/env bash
# Describe and safely audit the Brain executor-token secret.
# Never reads or prints secret values, creates tokens, or changes Control Plane config.
set -Eeuo pipefail
umask 077

REPO="${GH_REPO:-omarenserat1980/MySimpleProject}"
ENVIRONMENT="windows-real-boot"
SECRET="BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED"
ENROLLMENTS_VAR="BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON"

printf '%s\n' "Electronic Brain — Executor Token Secret Audit"
printf 'REPOSITORY=%s\nENVIRONMENT=%s\nSECRET_NAME=%s\n' "$REPO" "$ENVIRONMENT" "$SECRET"
printf '%s\n'   'PURPOSE=Bearer credential for one enrolled cloud executor to authenticate to the Brain attestation registry.'   'VALIDATION=Control Plane hashes the supplied token with SHA-256 and compares it with the enrolled executor ID digest.'   'SOURCE=Generate on a trusted management host; deliver to executor and GitHub Environment through approved secret channels.'   'NOT_A_VALUE=This script will not generate, retrieve, print, or guess the token.'   'GITHUB_LIMIT=GitHub Actions secret values cannot be retrieved after saving; only names can be listed.'

if ! command -v gh >/dev/null 2>&1; then
  echo 'RESULT=BLOCKED_GH_CLI_MISSING'
  exit 2
fi
if ! gh auth status >/dev/null 2>&1; then
  echo 'RESULT=BLOCKED_GH_NOT_AUTHENTICATED'
  exit 2
fi
if ! gh repo view "$REPO" --json nameWithOwner >/dev/null 2>&1; then
  echo 'RESULT=BLOCKED_REPOSITORY_ACCESS'
  exit 2
fi

names="$(gh secret list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name')" || {
  echo 'RESULT=BLOCKED_CANNOT_LIST_ENVIRONMENT_SECRET_NAMES'
  exit 2
}
if grep -Fxq "$SECRET" <<< "$names"; then
  echo 'GITHUB_SECRET_NAME=PRESENT'
  echo 'GITHUB_SECRET_VALUE=UNREADABLE_BY_DESIGN'
else
  echo 'GITHUB_SECRET_NAME=MISSING'
fi

echo
echo "CONTROL_PLANE_ENROLLMENT_VARIABLE=$ENROLLMENTS_VAR"
if grep -R -l --exclude-dir=.git "$ENROLLMENTS_VAR" brain_v12 2>/dev/null | head -n 1 | grep -q .; then
  echo 'LOCAL_SOURCE_REFERENCE=FOUND'
else
  echo 'LOCAL_SOURCE_REFERENCE=NOT_FOUND_IN_THIS_CHECKOUT'
fi

cat <<'NEXT'
NEXT_STEPS:
1. Confirm the authoritative HTTPS Control Plane is deployed and the executor ID/host binding is approved.
2. Generate a high-entropy per-executor token on the trusted management host.
3. Configure only its SHA-256 digest in BRAIN_CLOUD_EXECUTOR_ENROLLMENTS_SHA256_JSON on the Control Plane.
4. Deliver the raw token through the approved secure channel and save it as this GitHub Environment secret.
5. Verify a challenge request succeeds without logging the token.
Do not use a GitHub personal access token, a placeholder, or a token that is not enrolled.
This audit does not change secrets, enroll executors, issue contracts, or prove Windows boot.
NEXT

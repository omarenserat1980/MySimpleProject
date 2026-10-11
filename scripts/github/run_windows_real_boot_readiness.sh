#!/usr/bin/env bash
# Safely dispatch and observe the read-only Windows real-boot dependency gate.
# This tool never creates credentials, issues contracts, provisions cloud resources,
# starts a VM, or claims that Windows booted.
set -Eeuo pipefail
umask 077

REPO="${GH_REPO:-omarenserat1980/MySimpleProject}"
ENVIRONMENT="windows-real-boot"
WORKFLOW="brain-windows-real-boot-dependency-gate.yml"
MAX_POLLS="${BRAIN_GATE_MAX_POLLS:-90}"
POLL_SECONDS="${BRAIN_GATE_POLL_SECONDS:-5}"

die() { printf 'BLOCKED: %s\n' "$*" >&2; exit 2; }
command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) is required."
command -v python3 >/dev/null 2>&1 || die "python3 is required."
gh auth status >/dev/null 2>&1 || die "Authenticate using gh auth login first."
gh repo view "$REPO" --json nameWithOwner >/dev/null 2>&1 || die "Repository access unavailable."
gh workflow view "$WORKFLOW" --repo "$REPO" >/dev/null 2>&1 || die "Dependency-gate workflow unavailable on the selected repository/ref."

printf 'REPO=%s\nENVIRONMENT=%s\nWORKFLOW=%s\n' "$REPO" "$ENVIRONMENT" "$WORKFLOW"

# Report secret NAMES only. GitHub never returns secret values.
if ! secret_names="$(gh secret list --repo "$REPO" --env "$ENVIRONMENT" --json name --jq '.[].name' 2>/dev/null)"; then
  die "Cannot inspect environment secret names. Check repository/environment permissions."
fi
required=(
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED
  BRAIN_WINDOWS_CONTROL_PLANE_URL_PROTECTED
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
)
missing=0
for name in "${required[@]}"; do
  if grep -Fxq "$name" <<< "$secret_names"; then
    printf 'SECRET_NAME_PRESENT=%s\n' "$name"
  else
    printf 'SECRET_NAME_MISSING=%s\n' "$name"
    missing=$((missing + 1))
  fi
done
printf 'SECRET_NAME_MISSING_COUNT=%s\n' "$missing"
printf '%s\n' 'NOTE: presence does not prove that a secret value is correct or authorized.'

before="$(gh run list --repo "$REPO" --workflow "$WORKFLOW" --branch main --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId // 0')"
expected_sha="$(gh api "repos/$REPO/commits/main" --jq '.sha')"
[[ "$expected_sha" =~ ^[0-9a-f]{40}$ ]] || die "Could not resolve the current main commit."
printf 'EXPECTED_MAIN_SHA=%s\n' "$expected_sha"
printf 'DISPATCHING_READ_ONLY_GATE=YES\n'
gh workflow run "$WORKFLOW" --repo "$REPO" --ref main

run_id=""
for ((i=1; i<=MAX_POLLS; i++)); do
  latest="$(gh run list --repo "$REPO" --workflow "$WORKFLOW" --branch main --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId // 0' 2>/dev/null || printf '0')"
  if [[ "$latest" =~ ^[0-9]+$ ]] && [[ "$latest" != "0" ]] && [[ "$latest" != "$before" ]]; then
    run_id="$latest"
    break
  fi
  sleep "$POLL_SECONDS"
done
[[ -n "$run_id" ]] || die "Workflow dispatch was accepted, but its run ID was not observed within the polling window. Check Actions manually."

printf 'DEPENDENCY_GATE_RUN_ID=%s\n' "$run_id"
run_url="https://github.com/$REPO/actions/runs/$run_id"
printf 'DEPENDENCY_GATE_RUN_URL=%s\n' "$run_url"

for ((i=1; i<=MAX_POLLS; i++)); do
  row="$(gh run view "$run_id" --repo "$REPO" --json status,conclusion,headSha --jq '[.status // "",.conclusion // "",.headSha // ""] | join("|")')"
  IFS='|' read -r status conclusion run_sha <<< "$row"
  printf 'RUN_STATUS=%s RUN_CONCLUSION=%s\n' "${status:-unknown}" "${conclusion:-pending}"
  if [[ "$status" == "completed" ]]; then
    [[ "$run_sha" == "$expected_sha" ]] || die "Run SHA does not match the main commit observed before dispatch."
    if [[ "$conclusion" == "success" ]]; then
      printf 'DEPENDENCY_GATE=PASS\n'
      printf '%s\n' 'NEXT: separately verify signed contract issuance and trusted executor readiness.'
      printf '%s\n' 'WINDOWS_SERVER_2025_BOOT=NOT_VERIFIED'
      exit 0
    fi
    printf 'DEPENDENCY_GATE=BLOCKED\n'
    printf 'INSPECT_RUN=%s\n' "$run_url"
    printf '%s\n' 'No contract was issued and no VM boot was attempted by this tool.'
    exit 2
  fi
  sleep "$POLL_SECONDS"
done

printf 'DEPENDENCY_GATE=STILL_RUNNING\n'
printf 'INSPECT_RUN=%s\n' "$run_url"
printf '%s\n' 'No contract was issued and no VM boot was attempted by this tool.'
exit 3

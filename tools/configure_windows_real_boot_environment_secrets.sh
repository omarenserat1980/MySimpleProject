#!/usr/bin/env bash
# Securely configure the six Windows real-boot GitHub Environment secrets.
# Run from a trusted operator terminal with gh authenticated to the target repo.
# Values are read silently and piped to gh; they are never written to files or echoed.
set -euo pipefail
set +x

repo="${GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
environment="windows-real-boot"

command -v gh >/dev/null 2>&1 || { echo "BLOCKED: gh CLI is required."; exit 2; }
gh auth status >/dev/null 2>&1 || { echo "BLOCKED: authenticate gh to the repository first."; exit 2; }
gh api "repos/$repo/environments/$environment" >/dev/null 2>&1 || {
  echo "BLOCKED: repository/environment access check failed."
  exit 2
}

names=(
  BRAIN_CLOUD_EXECUTOR_REGISTRY_URL_PROTECTED
  BRAIN_CLOUD_EXECUTOR_TOKEN_PROTECTED
  BRAIN_CLOUD_EXECUTOR_ATTESTATION_PUBLIC_KEY_B64_PROTECTED
  BRAIN_AUTHORITY_PUBLIC_KEY_B64_PROTECTED
  BRAIN_WINDOWS_CONTRACT_DELIVERY_KEY_PROTECTED
)

echo "Configuring required secrets in GitHub Environment: $environment"
echo "Enter the existing authorized values from your trusted secret manager/control plane."
echo "Values are hidden while typing and are not saved to disk or printed."
for name in "${names[@]}"; do
  value=""
  while [[ -z "$value" ]]; do
    IFS= read -r -s -p "$name: " value
    printf '\n'
    [[ -n "$value" ]] || echo "Empty values are not accepted."
  done
  if ! printf '%s' "$value" | gh secret set "$name" --repo "$repo" --env "$environment" >/dev/null; then
    unset value
    echo "BLOCKED: could not set $name. No secret value was printed."
    exit 2
  fi
  unset value
  echo "SET $name"
done

echo
echo "Configured secret names (GitHub does not reveal values):"
gh secret list --repo "$repo" --env "$environment" --json name --jq '.[].name' | sort
echo
echo "NEXT: rerun Windows Real-Boot Runner Diagnostic and confirm all six inputs are present."
echo "This script does not issue an execution contract or start Windows boot."

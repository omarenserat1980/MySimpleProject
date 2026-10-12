#!/usr/bin/env bash
# Inspect whether the runner-watch GitHub Actions secret exists.
# GitHub never returns secret plaintext; this script intentionally does not print values.
set -euo pipefail
set +x
umask 077

REPO="${1:-omarenserat1980/MySimpleProject}"
SECRET_NAME="BRAIN_RUNNER_WATCH_TOKEN"

if ! command -v gh >/dev/null 2>&1; then
  echo "BLOCKED: install GitHub CLI (gh) and authenticate first."
  exit 2
fi

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "BLOCKED: run 'gh auth login' first."
  exit 3
fi

if ! SECRET_LIST="$(gh secret list --repo "$REPO" 2>/dev/null)"; then
  echo "BLOCKED: cannot list repository Actions secrets. Check repository access and Actions-secrets read permission."
  exit 4
fi

if printf '%s\n' "$SECRET_LIST" | awk 'NR>1 {print $1}' | grep -Fxq "$SECRET_NAME"; then
  echo "SECRET_CONFIGURED=true"
  echo "SECRET_NAME=$SECRET_NAME"
  echo "REPOSITORY=$REPO"
  echo "SECRET_VALUE=NOT_READABLE"
  echo "NOTE: GitHub Actions secrets are write-only; the original plaintext value cannot be retrieved."
  echo "NEXT: validate a token you control with scripts/github/create_runner_watch_secret.sh, which accepts hidden input and stores it securely."
else
  echo "SECRET_CONFIGURED=false"
  echo "SECRET_NAME=$SECRET_NAME"
  echo "REPOSITORY=$REPO"
  echo "NEXT: create a GitHub token with permission to read repository self-hosted runners, then run scripts/github/create_runner_watch_secret.sh."
fi

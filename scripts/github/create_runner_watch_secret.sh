#!/usr/bin/env bash
# Securely validate and store the Brain runner-watch token as a GitHub Actions secret.
# Never enable shell tracing (-x): this script handles a credential in memory.
set -euo pipefail
set +x
umask 077

REPO="${1:-omarenserat1980/MySimpleProject}"
SECRET_NAME="BRAIN_RUNNER_WATCH_TOKEN"
API_PATH="/repos/${REPO}/actions/runners?per_page=1"

if ! command -v gh >/dev/null 2>&1; then
  echo "BLOCKED: GitHub CLI (gh) is required. Install it and authenticate first." >&2
  exit 2
fi

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "BLOCKED: authenticate gh first with a credential allowed to write repository Actions secrets." >&2
  exit 3
fi

printf 'Paste the runner-watch token (input hidden): '
IFS= read -r -s WATCH_TOKEN
printf '\n'
if [[ -z "${WATCH_TOKEN}" ]]; then
  echo "BLOCKED: empty token; no secret was changed." >&2
  exit 4
fi

cleanup() { unset WATCH_TOKEN; }
trap cleanup EXIT

# Validate the candidate token against the exact endpoint before storing it.
# The token is passed via a child-process environment variable, never an argument
# and never printed. API errors are intentionally sanitized.
if ! RUNNERS_JSON="$(GH_TOKEN="${WATCH_TOKEN}" gh api "${API_PATH}" 2>/dev/null)"; then
  echo "BLOCKED: candidate token cannot read the repository runner endpoint; secret was not changed." >&2
  exit 5
fi
unset RUNNERS_JSON

# gh secret set reads the value from stdin and encrypts it for GitHub.
# The current gh-authenticated identity must have permission to write Actions secrets.
if ! printf '%s' "${WATCH_TOKEN}" | gh secret set "${SECRET_NAME}" --repo "${REPO}" >/dev/null; then
  echo "FAILED: validation passed, but GitHub rejected writing the Actions secret. Check the gh-authenticated account's Actions-secrets write permission. Token was not printed." >&2
  exit 6
fi

unset WATCH_TOKEN
trap - EXIT
echo "SECRET_WRITE=SUCCESS"
echo "SECRET_NAME=${SECRET_NAME}"
echo "REPOSITORY=${REPO}"
echo "NEXT: run the Brain Permanent Runner System Watch workflow and verify HTTP 403 is gone."

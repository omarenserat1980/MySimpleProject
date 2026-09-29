#!/data/data/com.termux/files/usr/bin/bash
# Source this file in the SAME Termux shell after gh auth login.
# It never prints the token.
set -euo pipefail
if ! command -v gh >/dev/null 2>&1; then
  echo "GH_CLI_MISSING: install with: pkg install gh" >&2
  return 2 2>/dev/null || exit 2
fi
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  echo "GH_NOT_AUTHENTICATED: run: gh auth login --hostname github.com --git-protocol https --web" >&2
  return 3 2>/dev/null || exit 3
fi
export GH_TOKEN="$(gh auth token --hostname github.com)"
if [ -z "$GH_TOKEN" ]; then
  echo "GH_TOKEN_MISSING" >&2
  return 4 2>/dev/null || exit 4
fi
export BRAIN_GITHUB_TOKEN="$GH_TOKEN"
export BRAIN_GITHUB_REPOSITORY="${BRAIN_GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
echo "BRAIN_GITHUB_SESSION=READY"
echo "BRAIN_GITHUB_REPOSITORY=$BRAIN_GITHUB_REPOSITORY"

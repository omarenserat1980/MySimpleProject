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
export GITHUB_TOKEN="$GH_TOKEN"
if [ -z "$GH_TOKEN" ]; then
  echo "GH_TOKEN_MISSING" >&2
  return 4 2>/dev/null || exit 4
fi
export BRAIN_GITHUB_TOKEN="$GH_TOKEN"
export BRAIN_GITHUB_REPOSITORY="${BRAIN_GITHUB_REPOSITORY:-omarenserat1980/MySimpleProject}"
export BRAIN_EMULATOR_KEY_FILE="${BRAIN_EMULATOR_KEY_FILE:-$HOME/.brain/secrets/termux_agent.key}"
echo "BRAIN_GITHUB_SESSION=READY"
if [ -f "brain_v12/ci/brain_github_auth.py" ]; then
  python brain_v12/ci/brain_github_auth.py
fi
if [ -n "${BRAIN_EMULATOR_KEY_FILE:-}" ] && [ -f "$BRAIN_EMULATOR_KEY_FILE" ]; then
  export BRAIN_EMULATOR_KEY="$(cat "$BRAIN_EMULATOR_KEY_FILE")"
  echo "BRAIN_TERMUX_AUTH=READY"
else
  echo "BRAIN_TERMUX_AUTH=NOT_CONFIGURED"
fi
echo "BRAIN_GITHUB_REPOSITORY=$BRAIN_GITHUB_REPOSITORY"

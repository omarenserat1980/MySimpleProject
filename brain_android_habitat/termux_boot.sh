#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# BRAIN Android Habitat — Termux:Boot entrypoint.
# This script must be launched by Termux itself (not Desktop Commander).
# It preserves Android/Termux security boundaries and starts the Brain-owned
# runtime launcher, which performs identity, connectivity, authentication and
# self-test checks before the agent can become READY.

ROOT="$HOME/MySimpleProject"
LAUNCHER="$ROOT/brain_v12/tools/brain_runtime_launcher.sh"

if [ ! -d "$ROOT" ]; then
  echo "BRAIN_HABITAT_ERROR: REPOSITORY_NOT_FOUND: $ROOT" >&2
  exit 20
fi
if [ ! -x "$LAUNCHER" ]; then
  chmod +x "$LAUNCHER" 2>/dev/null || true
fi
if [ ! -f "$LAUNCHER" ]; then
  echo "BRAIN_HABITAT_ERROR: LAUNCHER_NOT_FOUND: $LAUNCHER" >&2
  exit 21
fi

mkdir -p "$ROOT/.brain/state"
exec "$LAUNCHER" >> "$ROOT/.brain/state/termux-boot.log" 2>&1

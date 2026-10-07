#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Brain One-Boot: one command to bring up the persistent local Brain stack.
# It never rebuilds APKs, never exposes secrets, and never deletes project data.
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE="$ROOT/.brain/state"
mkdir -p "$STATE"

PIDFILE="$STATE/one_boot.pid"
if [ -s "$PIDFILE" ]; then
  OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "BRAIN_ONE_BOOT already_running=true pid=$OLD_PID"
    exit 0
  fi
fi
echo "$$" > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT INT TERM

export BRAIN_ONE_BOOT=1
export BRAIN_ROOT="$ROOT"

# The canonical launcher owns API/auth/supervisor/Termux-agent recovery.
"$ROOT/brain_v12/tools/brain_runtime_launcher.sh" >"$STATE/one_boot.log" 2>&1 &
RUNTIME_PID=$!

echo "BRAIN_ONE_BOOT started pid=$RUNTIME_PID"

PYTHON="$(command -v python3 || command -v python || true)"
if [ -n "$PYTHON" ]; then
  for _ in $(seq 1 20); do
    if "$PYTHON" "$ROOT/brain_v12/tools/brain_one_boot_verify.py" >>"$STATE/one_boot_verify.log" 2>&1; then
      echo "BRAIN_ONE_BOOT verified=true"
      break
    fi
    sleep 1
  done
fi

wait "$RUNTIME_PID"

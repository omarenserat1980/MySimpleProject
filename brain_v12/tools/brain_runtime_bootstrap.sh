#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/MySimpleProject"
LAUNCHER="$ROOT/brain_v12/tools/brain_runtime_launcher.sh"
STATE="$ROOT/.brain/state"
PID_FILE="$STATE/runtime-bootstrap.pid"
LOG_FILE="$STATE/runtime-bootstrap.log"

mkdir -p "$STATE"

if [ ! -x "$LAUNCHER" ]; then
  echo "BRAIN_RUNTIME_BOOTSTRAP_ERROR=LAUNCHER_NOT_EXECUTABLE" >&2
  exit 41
fi

if /system/bin/toybox nc -z 127.0.0.1 8012 >/dev/null 2>&1; then
  echo "BRAIN_RUNTIME_ALREADY_LISTENING=1"
  exit 0
fi

if [ -s "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "BRAIN_RUNTIME_START_IN_PROGRESS=1"
    exit 0
  fi
fi

nohup "$LAUNCHER" >>"$LOG_FILE" 2>&1 </dev/null &
PID=$!
echo "$PID" > "$PID_FILE"

sleep 2
if ! kill -0 "$PID" 2>/dev/null; then
  echo "BRAIN_RUNTIME_BOOTSTRAP_ERROR=LAUNCHER_EXITED" >&2
  tail -n 40 "$LOG_FILE" >&2 || true
  exit 43
fi

echo "BRAIN_RUNTIME_BOOTSTRAP_STARTED=1"
echo "BRAIN_RUNTIME_PID=$PID"
exit 0

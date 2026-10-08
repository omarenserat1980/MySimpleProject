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

ensure_supervisor() {
  local root="$ROOT"
  local state="$STATE"
  local pid_file="$state/supervisor.pid"
  local pid=""
  if [ -s "$pid_file" ]; then
    pid="$(cat "$pid_file" 2>/dev/null || true)"
  fi
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "BRAIN_RUNTIME_SUPERVISOR_ALIVE=1"
    return 0
  fi
  rm -f "$pid_file"
  local python="$(command -v python3 || command -v python || true)"
  if [ -z "$python" ]; then
    echo "BRAIN_RUNTIME_SUPERVISOR_CHECK=PYTHON_NOT_FOUND" >&2
    return 0
  fi
  mkdir -p "$state"
  "$python" "$root/brain_v12/tools/brain_runtime_supervisor.py" >>"$state/supervisor.log" 2>&1 &
  pid=$!
  echo "$pid" > "$pid_file"
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    echo "BRAIN_RUNTIME_SUPERVISOR_RECOVERED=1"
  else
    echo "BRAIN_RUNTIME_SUPERVISOR_RECOVERY_FAILED=1" >&2
  fi
}

if /system/bin/toybox nc -z 127.0.0.1 8012 >/dev/null 2>&1; then
  echo "BRAIN_RUNTIME_ALREADY_LISTENING=1"
  ensure_supervisor
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

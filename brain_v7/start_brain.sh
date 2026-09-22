#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Electronic Brain V11.3 / Android ==="

if ! command -v python >/dev/null 2>&1; then
  echo "Python غير مثبت. نفّذ: pkg install python"
  exit 1
fi

if ! python -c "import fastapi,pydantic,uvicorn,httpx" >/dev/null 2>&1; then
  echo "Installing Android-safe Python dependencies..."
  python -m pip install -r requirements.txt || exit 1
fi

TOKEN_FILE="$ROOT/.agent_token"
if [ ! -f "$TOKEN_FILE" ]; then
  TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
  printf '%s' "$TOKEN" > "$TOKEN_FILE"
  chmod 600 "$TOKEN_FILE"
else
  TOKEN="$(cat "$TOKEN_FILE")"
fi

export AGENT_TOKEN="$TOKEN"
export AGENT_URL="http://127.0.0.1:9000"
export AGENT_PORT="9000"
export PORT="8000"
export RELAY_ID="${RELAY_ID:-android-brain-01}"

port_open() {
  python - "$1" <<'PY'
import socket,sys
s=socket.socket()
s.settimeout(0.5)
try:
    s.connect(("127.0.0.1", int(sys.argv[1])))
    print("yes")
except OSError:
    print("no")
finally:
    s.close()
PY
}

cleanup() {
  [ -n "${OWN_AGENT_PID:-}" ] && kill "$OWN_AGENT_PID" 2>/dev/null || true
  [ -n "${OWN_RELAY_PID:-}" ] && kill "$OWN_RELAY_PID" 2>/dev/null || true
  [ -n "${OWN_BRAIN_PID:-}" ] && kill "$OWN_BRAIN_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Agent: $AGENT_URL"
echo "Brain: http://127.0.0.1:8000"

OWN_AGENT_PID=""
if [ "$(port_open 9000)" = "yes" ]; then
  echo "Agent already running on 9000 — reusing it."
else
  python run_agent.py &
  OWN_AGENT_PID=$!
  sleep 1
  if [ "$(port_open 9000)" != "yes" ]; then
    echo "ERROR: Agent failed to start on 9000."
    exit 1
  fi
fi

OWN_RELAY_PID=""
if [ -n "${RELAY_URL:-}" ] && [ -n "${RELAY_TOKEN:-}" ]; then
  if pgrep -f "python.*-m braincore_v2.relay_client" >/dev/null 2>&1; then
    echo "Relay client already running — reusing it."
  else
    python -m braincore_v2.relay_client &
    OWN_RELAY_PID=$!
    echo "Relay started."
  fi
else
  echo "Relay: disabled (set RELAY_URL and RELAY_TOKEN to enable)"
fi

if [ "$(port_open 8000)" = "yes" ]; then
  echo "Brain already running on 8000 — reusing it."
  echo "Electronic Brain is already active."
  while [ "$(port_open 8000)" = "yes" ]; do
    sleep 2
  done
  echo "Brain process ended."
  exit 0
fi

echo "Starting Brain Core..."
python main.py &
OWN_BRAIN_PID=$!

sleep 1
if [ "$(port_open 8000)" != "yes" ]; then
  echo "ERROR: Brain Core failed to start on 8000."
  exit 1
fi

echo "Electronic Brain V11.3 is RUNNING."
echo "اضغط Ctrl+C لإيقاف النسخة التي شغّلها هذا السكربت."

wait "$OWN_BRAIN_PID"
RC=$?
echo "Brain Core stopped (exit=$RC)."
exit "$RC"

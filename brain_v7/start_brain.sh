#!/data/data/com.termux/files/usr/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=== Electronic Brain V7 / Android ==="

if ! command -v python >/dev/null 2>&1; then
  echo "Python غير مثبت. نفّذ: pkg install python"
  exit 1
fi

# Install only when the required imports are missing.
# This avoids pulling Rust-based watchfiles on Android/Termux.
if ! python -c "import fastapi,pydantic,uvicorn,httpx" >/dev/null 2>&1; then
  echo "Installing Android-safe Python dependencies..."
  python -m pip install -r requirements.txt
fi

TOKEN_FILE="$ROOT/.agent_token"
if [ ! -f "$TOKEN_FILE" ]; then
  echo "أنشئ رمز Agent محلي."
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

echo "Agent: $AGENT_URL"
echo "Brain: http://127.0.0.1:8000"
if [ -n "${RELAY_URL:-}" ] && [ -n "${RELAY_TOKEN:-}" ]; then
  echo "Relay: $RELAY_URL ($RELAY_ID)"
else
  echo "Relay: disabled (set RELAY_URL and RELAY_TOKEN to enable)"
fi
echo "اضغط Ctrl+C لإيقاف العقل."

python run_agent.py &
AGENT_PID=$!

RELAY_PID=""
if [ -n "${RELAY_URL:-}" ] && [ -n "${RELAY_TOKEN:-}" ]; then
  python -m braincore_v2.relay_client &
  RELAY_PID=$!
fi

cleanup() {
  kill "$AGENT_PID" 2>/dev/null || true
  if [ -n "$RELAY_PID" ]; then kill "$RELAY_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

sleep 2
python main.py

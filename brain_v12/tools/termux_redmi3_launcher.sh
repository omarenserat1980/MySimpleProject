#!/data/data/com.termux/files/usr/bin/sh
# Start the existing allowlisted Brain agent from Termux itself.
# This script does not change Android permissions, UID, or sandbox settings.
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
: "${V12_BRAIN_URL:=https://brain-control-plane-main.onrender.com}"
: "${V12_AGENT_ID:=redmi3-01}"
: "${V12_AGENT_KEY_FILE:=$HOME/v12-agent/agent.key}"
export V12_BRAIN_URL V12_AGENT_ID V12_AGENT_KEY_FILE

if ! command -v python >/dev/null 2>&1; then
  echo "STOP: Python is not available in this Termux session."
  exit 10
fi
if [ ! -r "$V12_AGENT_KEY_FILE" ]; then
  echo "STOP: agent key file is missing or unreadable: $V12_AGENT_KEY_FILE"
  exit 11
fi

# This performs health/status reads and sends exactly one authenticated
# heartbeat. It never polls the queue or executes a task.
python "$SCRIPT_DIR/brain_device_preflight.py" --heartbeat || {
  echo "STOP: preflight failed; agent loop was not started."
  exit 12
}

exec python "$SCRIPT_DIR/brain_emulator_agent.py"

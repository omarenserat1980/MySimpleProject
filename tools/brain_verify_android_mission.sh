#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/MySimpleProject"
source "$HOME/.brain_env"
source "$HOME/v12-agent/agent_config.sh"
: "${BRAIN_CONTROL_KEY:?BRAIN_CONTROL_KEY missing}"
BASE="${V12_BRAIN_URL:-http://127.0.0.1:8012}"
PAYLOAD='{"task":"open_app","params":{"package":"com.android.settings"}}'
R="$(curl -fsS -X POST "$BASE/api/device/enqueue" -H 'Content-Type: application/json' -H "X-Brain-Control-Key: $BRAIN_CONTROL_KEY" -d "$PAYLOAD")"
echo "ENQUEUE=$R"
TASK_ID="$(printf '%s' "$R" | sed -n 's/.*"task_id":"\([^"]*\)".*/\1/p')"
test -n "$TASK_ID"
for i in $(seq 1 10); do
  RESULT="$(curl -fsS "$BASE/api/device/result/$TASK_ID")"
  echo "CHECK=$i RESULT=$RESULT"
  case "$RESULT" in
    *'"status":"COMPLETED"'*) exit 0;;
    *'"status":"FAILED"'*) exit 2;;
  esac
  sleep 1
done
echo "TIMEOUT task=$TASK_ID"
exit 3

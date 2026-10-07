#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
SOURCE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$SOURCE_ROOT"

# Runtime is isolated from the active development branch. The source manager
# fetches origin/main into a detached worktree and never rewrites local work.
if ! source "$SOURCE_ROOT/brain_v12/tools/brain_runtime_source_manager.sh"; then
  echo "BRAIN_RUNTIME_ERROR: SOURCE_CONVERGENCE_FAILED" >&2
  exit 49
fi
ROOT="${BRAIN_RUNTIME_ROOT}"
cd "$ROOT"
if [ -f "$HOME/.brain_env" ]; then . "$HOME/.brain_env"; fi
if [ -f "$HOME/v12-agent/agent_config.sh" ]; then . "$HOME/v12-agent/agent_config.sh"; fi
if [[ "${BRAIN_URL:-}" == *render.com* ]]; then unset BRAIN_URL; fi
if [[ "${V12_BRAIN_URL:-}" == *render.com* ]]; then unset V12_BRAIN_URL; fi
export V12_BRAIN_URL="${BRAIN_URL:-http://127.0.0.1:8012}"
export V12_AGENT_ID="${V12_AGENT_ID:-redmi3-01}"
export V12_AGENT_KEY_FILE="${V12_AGENT_KEY_FILE:-$HOME/v12-agent/agent.key}"
export BRAIN_AGENT_KEY_FILE="${V12_AGENT_KEY_FILE}"
mkdir -p "$(dirname "$V12_AGENT_KEY_FILE")"
if [ ! -s "$V12_AGENT_KEY_FILE" ]; then
  echo "JET_BRAIN_AUTH missing_key_creating_local_key" >&2
  PYTHON_BOOT="$(command -v python3 || command -v python || true)"
  if [ -z "$PYTHON_BOOT" ]; then echo "BRAIN_RUNTIME_ERROR: PYTHON_NOT_FOUND" >&2; exit 42; fi
  "$PYTHON_BOOT" -c 'import secrets,os; p=os.path.expanduser(os.environ["V12_AGENT_KEY_FILE"]); open(p,"w",encoding="utf-8").write(secrets.token_urlsafe(48)+"\n"); os.chmod(p,0o600)'
fi
if [ ! -s "$V12_AGENT_KEY_FILE" ]; then echo "BRAIN_RUNTIME_ERROR: AGENT_KEY_CREATE_FAILED" >&2; exit 41; fi
export BRAIN_EMULATOR_KEY="$(cat "$V12_AGENT_KEY_FILE")"
export PYTHONPATH="$ROOT:${PYTHONPATH:-}"
PYTHON="${V12_PYTHON_EXECUTABLE:-$(command -v python3 || command -v python)}"
if [ -z "$PYTHON" ]; then echo "BRAIN_RUNTIME_ERROR: PYTHON_NOT_FOUND" >&2; exit 42; fi
mkdir -p "$ROOT/.brain/state"
status_snapshot() {
  "$PYTHON" - <<'PY'
import json, os, urllib.request
base=os.environ["V12_BRAIN_URL"]
try:
    with urllib.request.urlopen(base+"/api/device/status", timeout=3) as r:
        data=json.loads(r.read().decode())
    print("JET_BRAIN_DEVICE_STATUS "+json.dumps(data, ensure_ascii=False, separators=(",",":")))
except Exception as exc:
    print("JET_BRAIN_DEVICE_STATUS_ERROR "+str(exc)[:200])
PY
}
health_ok() { "$PYTHON" -c 'import os,urllib.request; urllib.request.urlopen(os.environ["V12_BRAIN_URL"]+"/health",timeout=2).read()' >/dev/null 2>&1; }
auth_ok() {
  "$PYTHON" -c 'import json,os,urllib.request
key=open(os.path.expanduser(os.environ["V12_AGENT_KEY_FILE"]),encoding="utf-8").read().strip()
req=urllib.request.Request(os.environ["V12_BRAIN_URL"]+"/api/device/heartbeat",data=json.dumps({"agent_id":os.environ["V12_AGENT_ID"]}).encode(),headers={"Content-Type":"application/json","X-V12-Agent-Key":key},method="POST")
with urllib.request.urlopen(req,timeout=3) as r: r.read()' >/dev/null 2>&1
}
start_api() {
  echo "JET_BRAIN_API starting url=$V12_BRAIN_URL" >&2
  "$PYTHON" -m uvicorn brain_v12.app:app --host 127.0.0.1 --port 8012 --workers 1 --log-level warning >> "$ROOT/.brain/state/api.log" 2>&1 &
  API_PID=$!
  for i in $(seq 1 20); do if health_ok; then break; fi; sleep 1; done
  if ! health_ok; then echo "BRAIN_RUNTIME_ERROR: API_START_FAILED pid=$API_PID" >&2; exit 43; fi
  echo "JET_BRAIN_API ready pid=$API_PID" >&2
}
if health_ok; then
  if auth_ok; then echo "JET_BRAIN_API already_ready_and_authenticated url=$V12_BRAIN_URL" >&2
  else
    echo "JET_BRAIN_API stale_auth_restart" >&2
    pkill -f "uvicorn brain_v12.app:app --host 127.0.0.1 --port 8012" 2>/dev/null || true
    sleep 1
    start_api
  fi
else start_api; fi
if ! auth_ok; then echo "BRAIN_RUNTIME_ERROR: API_AUTH_FAILED" >&2; exit 44; fi

seed_bootstrap_task() {
  if [ -z "${BRAIN_CONTROL_KEY:-}" ]; then
    echo "JET_BRAIN_SUPERVISOR bootstrap_skipped_no_control_key" >&2
    return 0
  fi
  "$PYTHON" - <<'PY'
import json, os, urllib.request
base=os.environ["V12_BRAIN_URL"]
key=os.environ.get("BRAIN_CONTROL_KEY","")
headers={"Content-Type":"application/json","X-Brain-Control-Key":key}
try:
    req=urllib.request.Request(base+"/api/device/enqueue",data=json.dumps({"task":"brain_self_test","params":{}}).encode(),headers=headers,method="POST")
    with urllib.request.urlopen(req,timeout=5) as r:
        out=json.loads(r.read().decode())
    print("JET_BRAIN_SUPERVISOR bootstrap_task="+str(out.get("task",{}).get("task_id","UNKNOWN")),flush=True)
except Exception as exc:
    print("JET_BRAIN_SUPERVISOR bootstrap_failed="+str(exc)[:200],flush=True)
PY
}
status_snapshot
seed_bootstrap_task
# Do not start a second orchestration loop here.
# The canonical BrainSupervisor is owned by the Brain API runtime. The Android
# launcher starts only the API and the executor agent; continuous scheduling,
# repair and verification remain behind that single authority.
echo "JET_BRAIN_RUNTIME url=$V12_BRAIN_URL agent=$V12_AGENT_ID" >&2
exec "$PYTHON" "$ROOT/brain_v12/tools/brain_emulator_agent.py"

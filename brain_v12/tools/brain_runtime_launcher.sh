#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
SOURCE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$SOURCE_ROOT"

# Prefer the isolated runtime source manager when present. Older/local checkouts
# may not contain it; in that case run directly from the verified source tree.
SOURCE_MANAGER="$SOURCE_ROOT/brain_v12/tools/brain_runtime_source_manager.sh"
if [ -f "$SOURCE_MANAGER" ]; then
  if ! source "$SOURCE_MANAGER"; then
    echo "BRAIN_RUNTIME_ERROR: SOURCE_CONVERGENCE_FAILED" >&2
    exit 49
  fi
  ROOT="${BRAIN_RUNTIME_ROOT:-$SOURCE_ROOT}"
else
  echo "JET_BRAIN_SOURCE_SYNC fallback_local_root" >&2
  ROOT="$SOURCE_ROOT"
fi
cd "$ROOT"
if [ -f "$HOME/.brain_env" ]; then . "$HOME/.brain_env"; fi
if [ -f "$HOME/v12-agent/agent_config.sh" ]; then . "$HOME/v12-agent/agent_config.sh"; fi
if [[ "${BRAIN_URL:-}" == *render.com* ]]; then unset BRAIN_URL; fi
if [[ "${V12_BRAIN_URL:-}" == *render.com* ]]; then unset V12_BRAIN_URL; fi
# Preserve an explicit non-paid endpoint from either supported variable.
# Render guards above run first, so blocked paid endpoints cannot be restored here.
export V12_BRAIN_URL="${V12_BRAIN_URL:-${BRAIN_URL:-http://127.0.0.1:8012}}"
# Local Termux runtime must use exactly one on-device key. Clear stale values, then seed the direct-key variable from the canonical local key file.
unset BRAIN_AGENT_KEY BRAIN_AGENT_KEY_SHA256 BRAIN_EMULATOR_KEY
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
# DeviceBridge checks BRAIN_AGENT_KEY first; explicitly bind it to the same local key.
export BRAIN_AGENT_KEY="$BRAIN_EMULATOR_KEY"
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
auth_diagnostic() {
  "$PYTHON" - <<'PY'
import json, os, socket, urllib.error, urllib.request
base = os.environ["V12_BRAIN_URL"]
try:
    key = open(os.path.expanduser(os.environ["V12_AGENT_KEY_FILE"]), encoding="utf-8").read().strip()
    req = urllib.request.Request(
        base + "/api/device/heartbeat",
        data=json.dumps({"agent_id": os.environ["V12_AGENT_ID"]}).encode(),
        headers={"Content-Type": "application/json", "X-V12-Agent-Key": key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=3) as response:
        response.read()
    print("JET_BRAIN_AUTH_DIAGNOSTIC status=AUTH_OK")
except urllib.error.HTTPError as exc:
    print("JET_BRAIN_AUTH_DIAGNOSTIC status=HTTP_" + str(exc.code))
except urllib.error.URLError as exc:
    reason = exc.reason
    if isinstance(reason, (socket.timeout, TimeoutError)):
        status = "TIMEOUT"
    elif isinstance(reason, ConnectionRefusedError):
        status = "CONNECTION_REFUSED"
    else:
        status = "NETWORK_ERROR"
    print("JET_BRAIN_AUTH_DIAGNOSTIC status=" + status)
except (OSError, ValueError) as exc:
    print("JET_BRAIN_AUTH_DIAGNOSTIC status=LOCAL_CONFIG_ERROR type=" + type(exc).__name__)
except Exception as exc:
    print("JET_BRAIN_AUTH_DIAGNOSTIC status=UNEXPECTED_ERROR type=" + type(exc).__name__)
PY
}
start_api() {
  echo "JET_BRAIN_API starting url=$V12_BRAIN_URL" >&2
  "$PYTHON" -m uvicorn brain_v12.app:app --host 127.0.0.1 --port 8012 --workers 1 --log-level warning >> "$ROOT/.brain/state/api.log" 2>&1 &
  API_PID=$!
  for i in $(seq 1 20); do
    if ! kill -0 "$API_PID" 2>/dev/null; then
      echo "BRAIN_RUNTIME_ERROR: API_PROCESS_EXITED pid=$API_PID" >&2
      tail -n 40 "$ROOT/.brain/state/api.log" >&2 || true
      exit 43
    fi
    if health_ok; then break; fi
    sleep 1
  done
  if ! kill -0 "$API_PID" 2>/dev/null; then
    echo "BRAIN_RUNTIME_ERROR: API_PROCESS_EXITED pid=$API_PID" >&2
    tail -n 40 "$ROOT/.brain/state/api.log" >&2 || true
    exit 43
  fi
  if ! health_ok; then echo "BRAIN_RUNTIME_ERROR: API_START_FAILED pid=$API_PID" >&2; exit 43; fi
  echo "JET_BRAIN_API ready pid=$API_PID" >&2
}
is_local_api() {
  "$PYTHON" -c 'import ipaddress,os,urllib.parse
host=(urllib.parse.urlparse(os.environ["V12_BRAIN_URL"]).hostname or "").lower()
if host == "localhost": raise SystemExit(0)
try: raise SystemExit(0 if ipaddress.ip_address(host).is_loopback else 1)
except ValueError: raise SystemExit(1)' 
}
if is_local_api; then
  if health_ok; then
    if auth_ok; then
      echo "JET_BRAIN_API already_ready_and_authenticated url=$V12_BRAIN_URL" >&2
    else
      echo "JET_BRAIN_API local_auth_failed_restart_once" >&2
      pkill -f '[u]vicorn brain_v12.app:app --host 127.0.0.1 --port 8012' 2>/dev/null || true
      sleep 1
      start_api
    fi
  else
    start_api
  fi
else
  # A remote endpoint must never trigger launch/kill of the local API process.
  if ! health_ok; then
    auth_diagnostic >&2 || true
    echo "BRAIN_RUNTIME_ERROR: REMOTE_API_UNREACHABLE url=$V12_BRAIN_URL" >&2
    exit 43
  fi
  echo "JET_BRAIN_API remote_endpoint_reachable url=$V12_BRAIN_URL" >&2
fi
if ! auth_ok; then
  auth_diagnostic >&2 || true
  echo "BRAIN_RUNTIME_ERROR: API_AUTH_FAILED" >&2
  exit 44
fi

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
# Keep exactly one durable local supervisor alongside the Emulator.
if [ -n "${BRAIN_CONTROL_KEY:-}" ]; then
  SUP_PID_FILE="$ROOT/.brain/state/supervisor.pid"
  SUP_PID=""
  if [ -s "$SUP_PID_FILE" ]; then SUP_PID="$(cat "$SUP_PID_FILE" 2>/dev/null || true)"; fi
  if [ -n "$SUP_PID" ] && kill -0 "$SUP_PID" 2>/dev/null; then
    echo "JET_BRAIN_SUPERVISOR already_running pid=$SUP_PID" >&2
  else
    rm -f "$SUP_PID_FILE"
    "$PYTHON" "$ROOT/brain_v12/tools/brain_runtime_supervisor.py" >> "$ROOT/.brain/state/supervisor.log" 2>&1 &
    SUPERVISOR_PID=$!
    echo "$SUPERVISOR_PID" > "$SUP_PID_FILE"
    echo "JET_BRAIN_SUPERVISOR pid=$SUPERVISOR_PID" >&2
  fi
fi
echo "JET_BRAIN_RUNTIME url=$V12_BRAIN_URL agent=$V12_AGENT_ID" >&2
exec "$PYTHON" "$ROOT/brain_v12/tools/brain_emulator_agent.py"

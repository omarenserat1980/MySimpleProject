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
# Keep the established development database when running the isolated runtime
# worktree. Never silently create a fresh empty DB in the runtime checkout.
if [ -z "${BRAIN_DB:-}" ] && [ -s "$SOURCE_ROOT/brain_v12/brain_v12.db" ]; then
  export BRAIN_DB="$SOURCE_ROOT/brain_v12/brain_v12.db"
fi
if [ -f "$HOME/.brain_env" ]; then . "$HOME/.brain_env"; fi
if [ -f "$HOME/v12-agent/agent_config.sh" ]; then . "$HOME/v12-agent/agent_config.sh"; fi
if [[ "${BRAIN_URL:-}" == *render.com* ]]; then unset BRAIN_URL; fi
if [[ "${V12_BRAIN_URL:-}" == *render.com* ]]; then unset V12_BRAIN_URL; fi

# Resolve a stable per-device logical ID before applying defaults. Never let a
# copied Redmi config silently register another handset as redmi3-01.
DEVICE_MODEL="$(getprop ro.product.model 2>/dev/null || true)"
DETECTED_AGENT_ID=""
# Only exact known hardware model identifiers are auto-mapped. Brand-name
# matching is deliberately avoided because multiple phones can share a brand.
# Unknown models must use an explicitly configured, unique V12_AGENT_ID.
case "$DEVICE_MODEL" in
  *23129RN51X*) DETECTED_AGENT_ID="redmi3-01" ;;
  *RMX3710*) DETECTED_AGENT_ID="realme-01" ;;
esac
if [ -n "$DETECTED_AGENT_ID" ]; then
  if [ -n "${V12_AGENT_ID:-}" ] && [ "$V12_AGENT_ID" != "$DETECTED_AGENT_ID" ]; then
    echo "BRAIN_RUNTIME_ERROR: DEVICE_ID_MISMATCH model=$DEVICE_MODEL configured=$V12_AGENT_ID expected=$DETECTED_AGENT_ID" >&2
    echo "Fix $HOME/v12-agent/agent_config.sh locally; do not copy another device's ID or key." >&2
    exit 45
  fi
  export V12_AGENT_ID="$DETECTED_AGENT_ID"
elif [ -z "${V12_AGENT_ID:-}" ]; then
  echo "BRAIN_RUNTIME_ERROR: DEVICE_ID_REQUIRED model=${DEVICE_MODEL:-unknown}; set a unique V12_AGENT_ID in $HOME/v12-agent/agent_config.sh" >&2
  exit 45
fi

# Preserve explicit non-paid endpoints. The default loopback endpoint is only
# valid for the primary Redmi that hosts this local API; loopback on Realme is
# Realme itself, not the Redmi Brain.
export V12_BRAIN_URL="${V12_BRAIN_URL:-${BRAIN_URL:-http://127.0.0.1:8012}}"
if [ "$V12_AGENT_ID" != "redmi3-01" ]; then
  case "$V12_BRAIN_URL" in
    http://localhost*|https://localhost*|http://127.*|https://127.*|http://\[::1\]*|https://\[::1\]*)
      echo "BRAIN_RUNTIME_ERROR: REMOTE_BRAIN_URL_REQUIRED agent=$V12_AGENT_ID url=$V12_BRAIN_URL" >&2
      echo "Set V12_BRAIN_URL to an already reachable, authenticated Brain endpoint in $HOME/v12-agent/agent_config.sh." >&2
      echo "No Redmi settings or credentials were changed by this launcher." >&2
      exit 46
      ;;
  esac
fi

# Keep a local key file for this runtime. Remote acceptance depends on the
# server's configured authentication policy; never copy another device's key
# just to bypass an authentication failure.
unset BRAIN_AGENT_KEY BRAIN_AGENT_KEY_SHA256 BRAIN_EMULATOR_KEY
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
RUNTIME_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
API_COMMIT_MARKER="$ROOT/.brain/state/api-runtime-commit"
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
  printf "%s\n" "$RUNTIME_COMMIT" > "$API_COMMIT_MARKER"
  echo "JET_BRAIN_API ready pid=$API_PID runtime_commit=$RUNTIME_COMMIT" >&2
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
      # A healthy API may still have old Python modules loaded even when its
      # working directory is unchanged. Compare the commit recorded at the
      # last successful launch with the currently converged runtime commit.
      API_PID_ACTIVE=""
      API_CWD=""
      for candidate_pid in $(pgrep -f '[u]vicorn brain_v12.app:app --host 127.0.0.1 --port 8012' 2>/dev/null || true); do
        candidate_cwd="$(readlink "/proc/$candidate_pid/cwd" 2>/dev/null || true)"
        if [ -n "$candidate_cwd" ]; then
          API_PID_ACTIVE="$candidate_pid"
          API_CWD="$candidate_cwd"
          break
        fi
      done
      RECORDED_COMMIT="$(cat "$API_COMMIT_MARKER" 2>/dev/null || true)"
      if [ "$RECORDED_COMMIT" != "$RUNTIME_COMMIT" ] || [ "$API_CWD" != "$ROOT" ]; then
        echo "JET_BRAIN_API restart_for_runtime_convergence old_commit=${RECORDED_COMMIT:-unknown} new_commit=$RUNTIME_COMMIT old_root=${API_CWD:-unknown} new_root=$ROOT" >&2
        pkill -f '[u]vicorn brain_v12.app:app --host 127.0.0.1 --port 8012' 2>/dev/null || true
        sleep 1
        start_api
      else
        echo "JET_BRAIN_API already_running_from_converged_root pid=$API_PID_ACTIVE runtime_commit=$RUNTIME_COMMIT" >&2
      fi
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

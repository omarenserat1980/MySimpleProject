#!/data/data/com.termux/files/usr/bin/bash
# Safe Termux recovery helper for the Brain device bridge.
# Downloads only the public read-only doctor; never prints or uploads agent.key.
set -u

REPO_RAW="https://raw.githubusercontent.com/omarenserat1980/MySimpleProject/main"
AGENT_HOME="${V12_AGENT_HOME:-$HOME/v12-agent}"
DOCTOR="$AGENT_HOME/brain_device_bridge_doctor.py"
KEY_FILE="${V12_AGENT_KEY_FILE:-$AGENT_HOME/agent.key}"
BRAIN_URL="${V12_BRAIN_URL:-https://electronic-brain-v12-gwwg.onrender.com}"
AGENT_ID="${V12_AGENT_ID:-redmi3-01}"

printf '%s\n' "BRAIN TERMUX RECOVERY PREFLIGHT (no settings changed)"
printf 'agent_home=%s\nbrain_url=%s\nagent_id=%s\n' "$AGENT_HOME" "$BRAIN_URL" "$AGENT_ID"

if ! command -v python >/dev/null 2>&1; then
  echo "BLOCKED: python is not available in PATH"
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "BLOCKED: curl is not available in PATH"
  exit 2
fi
if [ ! -d "$AGENT_HOME" ]; then
  echo "BLOCKED: expected agent directory is missing: $AGENT_HOME"
  echo "No directory was created; check the actual Termux agent location first."
  exit 3
fi

for file in agent.py agent_config.py agent.key; do
  if [ -s "$AGENT_HOME/$file" ]; then
    printf 'local_%s=FOUND_NONEMPTY\n' "$file"
  else
    printf 'local_%s=MISSING_OR_EMPTY\n' "$file"
  fi
done

tmp="$AGENT_HOME/.brain_device_bridge_doctor.py.tmp"
if ! curl --fail --silent --show-error --location --retry 2 --connect-timeout 10 --max-time 45 \
  "$REPO_RAW/brain_v12/tools/brain_device_bridge_doctor.py" -o "$tmp"; then
  rm -f "$tmp"
  echo "BLOCKED: could not download the public diagnostic script from GitHub"
  exit 4
fi
if ! python -m py_compile "$tmp"; then
  rm -f "$tmp"
  echo "BLOCKED: downloaded diagnostic failed Python syntax validation"
  exit 5
fi
mv -f "$tmp" "$DOCTOR" || exit 6
chmod 700 "$DOCTOR" 2>/dev/null || true
echo "doctor_script=DOWNLOADED_AND_COMPILED"

if [ ! -s "$KEY_FILE" ]; then
  echo "BLOCKED: agent key file is missing or empty; key contents were not read to output"
  exit 7
fi

exec python "$DOCTOR" --key-file "$KEY_FILE" --url "$BRAIN_URL" --agent-id "$AGENT_ID"
